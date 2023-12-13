from django.shortcuts import render, redirect
from django.views import View
from .models import User
from .models import Task
from .models import Pig
from .models import Sow
from .models import PigSale
from .models import Vaccine 
from .models import FeedsInventory  
from .models import MortalityForm
from .models import SowPerformance
from .models import FeedStockUpdate
from datetime import date, timedelta
from django.http import JsonResponse
from django.contrib.auth import authenticate, login
from django.db import transaction
import json
from django.db.models import Q
from django.contrib import messages
from datetime import date as today_date, timedelta
from django.db.models.functions import ExtractDay
from django.db.models import Sum, Avg, F, ExpressionWrapper, DecimalField, Max
from django.utils import timezone
import pandas as pd
from barcode import Code128
import barcode
from barcode import generate
from barcode.writer import ImageWriter
from io import BytesIO
import base64
from django.http import HttpResponse
from django.http import FileResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, TableStyle, Paragraph, Spacer
from reportlab.platypus.tables import Table
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from statistics import mean
from decimal import *
from itertools import chain
from django.db.models import Q, Max, Subquery
from django.db.models.functions import Coalesce
from django.db.models import DateField
from django.db.models import OuterRef


def generate_barcode(pig_id):
    # Create a Code128 barcode with the pig_id
    code128 = barcode.get_barcode_class('code128')
    code = code128(pig_id, writer=barcode.writer.ImageWriter(format='PNG'))
    
    # Render the barcode to an image and save it to a BytesIO buffer
    buffer = BytesIO()
    code.write(buffer)
    buffer.seek(0)  # Reset the buffer position

    # Read the BytesIO buffer and encode the image in base64
    barcode_image = base64.b64encode(buffer.getvalue())

    return barcode_image


def add_pigs(request, user_type):
    context = {
        'user_type': user_type,
    }
    if request.method == 'POST':
        # Handle form submission
        pig_id = request.POST.get("pigID")
        dam = request.POST.get("dam")
        dob = request.POST.get("dob")
        sire = request.POST.get("sire")
        pig_class = request.POST.get("class")
        sex = request.POST.get("sex")
        count = request.POST.get("count")
        weight = request.POST.get("weight")
        remarks = request.POST.get("remarks")
        verif_by = request.POST.get("verifBy")
        birthdate = request.POST.get("date")

        if not pig_id or pig_id.strip() == "":
            # Handle the case where pig_id is missing or empty
            return HttpResponse("Pig ID is required.")

        try:
            count = int(count)
            weight = float(weight)
        except (ValueError, TypeError):
            # Handle conversion errors
            return HttpResponse("Invalid count or weight.")

        # Create a Pig object and save it to the database
        pig = Pig(
            pig_id=pig_id,
            dam=dam,
            dob=dob,
            sire=sire,
            pig_class=pig_class,
            sex=sex,
            count=count,
            weight=weight,
            remarks=remarks,
            verif_by=verif_by,
            date=birthdate,
            barcode_image=generate_barcode(pig_id)
        )
        pig.save()
    
        # Redirect to prevent form resubmission
        return redirect('Add_Pigs', user_type=user_type)

    # Filter pigs by age groups
    twenty_eight_days_ago = date.today() - timedelta(days=28)
    eighty_eight_days_ago = date.today() - timedelta(days=88)
    one_fortyeight_days_ago = date.today() - timedelta(days=148)

    # Define the Q objects to filter pigs with PigSale or MortalityForm
    exclude_q = Q(pigsale__isnull=False) | Q(mortality_forms__isnull=False)

    # Filter pigs based on age groups while excluding those with PigSale or MortalityForm
    pig_list_28_days = Pig.objects.filter(dob__gte=twenty_eight_days_ago).exclude(exclude_q)
    pig_list_28_to_88_days = Pig.objects.filter(dob__gte=eighty_eight_days_ago, dob__lt=twenty_eight_days_ago).exclude(exclude_q)
    pig_list_88_to_148_days = Pig.objects.filter(dob__gte=one_fortyeight_days_ago, dob__lt=eighty_eight_days_ago).exclude(exclude_q)
    pig_list_greater_than_148_days = Pig.objects.filter(dob__lt=one_fortyeight_days_ago).exclude(exclude_q)

    # Filter the full pig list to exclude those with PigSale or MortalityForm
    pig_list = Pig.objects.all().exclude(exclude_q)
    sow_list = Sow.objects.all()
    pig_list_all = Pig.objects.all()

    context.update({
        'pig_list_28_days': pig_list_28_days,
        'pig_list_28_to_88_days': pig_list_28_to_88_days,
        'pig_list_88_to_148_days': pig_list_88_to_148_days,
        'pig_list_greater_than_148_days': pig_list_greater_than_148_days,
        'pig_list': pig_list,
        'sow_list': sow_list,
        'pig_list_all':pig_list_all,

    })

    return render(request, 'Farm/add_pigs.html', context)


def Login(request):
    return render(request, 'Authentication/Login.html')

def index(request, user_type):
    feed_stock = FeedsInventory.objects.all()
    updated_to_stock=FeedStockUpdate.objects.all()
    today = timezone.now().date()
    
    total_used = FeedStockUpdate.objects.aggregate(total_used=Sum('count_update'))['total_used'] or 0

    total_feed_quantity = feed_stock.aggregate(total_quantity=Sum('quantity'))['total_quantity'] or 0

    remaining_feed_quantity = total_feed_quantity - total_used

    # Define the Q object to filter pigs with PigSale or MortalityForm
    exclude_q = Q(pigsale__isnull=False) | Q(mortality_forms__isnull=False)
    
    # Fetch pig lists by days, excluding those with PigSale or MortalityForm
    eighty_eight_days_ago = date.today() - timedelta(days=88)
    pig_list_88_days = Pig.objects.filter(dob__gte=eighty_eight_days_ago).exclude(exclude_q)
    pig_list_more_88_days = Pig.objects.filter(dob__lt=eighty_eight_days_ago).exclude(exclude_q)
    pig_sales_price = PigSale.objects.values('date__year', 'date__month').annotate(total_price=Sum('price')).order_by('date__year', 'date__month')
    pig_sales_monthly_data = [{'year': sale['date__year'],'month': sale['date__month'],'total_price': float(sale['total_price']) }for sale in pig_sales_price]
    all_pigs = Pig.objects.count()
    all_sows = Sow.objects.count()

    today = date.today()
    today_tasks = Task.objects.filter(due_date=today)
    checked_tasks = Task.objects.filter(is_done=True)

    thirty_three_days_ago = timezone.now() - timedelta(days=33)
    due_filter = Q(date_due__gte=thirty_three_days_ago)
    farr_filter = Q(date_farr__gte=thirty_three_days_ago)
    combined_filter = due_filter | farr_filter
    sow_performance_count = SowPerformance.objects.filter(combined_filter).values('sow_no').distinct().count()


    total_sow_count = Sow.objects.count()

    sow_count_with_performance = sow_performance_count
    sow_count_without_performance = total_sow_count - sow_performance_count
    
    print(sow_count_with_performance)
    print(sow_count_without_performance)

    return render(request, 'Farm/index.html', {
        "today_tasks": today_tasks,
        "checked_tasks": checked_tasks,
        "user_type": user_type,
        "all_pigs":all_pigs,
        "all_sows": all_sows,
        "pig_list_88_days": pig_list_88_days,
        "pig_list_more_88_days": pig_list_more_88_days,
        "feed_stock": feed_stock,
        "remaining_feed_quantity": remaining_feed_quantity,
        "pig_sales_monthly_data":json.dumps(list(pig_sales_monthly_data)),
        "sow_count_without_performance":sow_count_without_performance
    })


def manage_user(request, user_type):
    if request.method == 'POST':
        # Handle user creation
        firstname = request.POST.get("firstname")
        lastname = request.POST.get("lastname")
        username = request.POST.get("username")
        password = request.POST.get("password")
        role = request.POST.get("role")
        date = request.POST.get("date")

        # If all required fields are provided, create a new User object and save it to the database
        if firstname and lastname and username and password and role and date:
            user = User(
                firstname=firstname,
                lastname=lastname,
                username=username,
                password=password,
                role=role,
                date=date
            )
            user.save()
            
            # Redirect to the same page to prevent form resubmission
            return redirect('manage_user', user_type=user_type)
     # Retrieve a queryset of User objects from your database
    all_user = User.objects.count()
    users = User.objects.filter(archive_user='False')
    users_in_archive = User.objects.filter(archive_user='True')
    users_count = User.objects.filter(role='user',  archive_user=False).count()
    users__in_archive_count = User.objects.filter(role='user',  archive_user=True).count()

    # Render the manage_user page
    return render(request, 'Farm/manage_user.html', {"users": users,"user_type": user_type, "users_count" :users_count, "users_in_archive":users_in_archive, "users__in_archive_count":users__in_archive_count, "all_user":all_user})

from collections import defaultdict
from datetime import datetime
from django.db.models import Count
from collections import Counter
from django.db.models import Avg

def reports(request, user_type):
    # Fetch Pig data and calculate monthly counts for pig registration
    pig_data = Pig.objects.all()
    exclude_q = Q(pigsale__isnull=False) | Q(mortality_forms__isnull=False)

    monthly_counts = defaultdict(int)

    for pig in pig_data:
        registration_date = pig.dob
        year_month = registration_date.strftime("%Y-%m")
        monthly_counts[year_month] += 1

    # Fetch PigSale data and calculate monthly sales counts
    sale_data = PigSale.objects.all()

    monthly_sale_counts = defaultdict(int)

    for sale in sale_data:
        sale_date = sale.date
        year_month = sale_date.strftime("%Y-%m")
        monthly_sale_counts[year_month] += 1

    pig_sales_data = PigSale.objects.values('date__year', 'date__month').annotate(average_weight=Avg('weight'))
    average_weights = {f"{data['date__year']}-{data['date__month']}": float(data['average_weight']) for data in pig_sales_data}
    pig_sales_price = PigSale.objects.values('date__year', 'date__month').annotate(total_price=Sum('price')).order_by('date__year', 'date__month')
    pig_sales_monthly_data = [{'year': sale['date__year'],'month': sale['date__month'],'total_price': float(sale['total_price']) }for sale in pig_sales_price]
    print( pig_sales_monthly_data)


    monthly_mortality_counts = defaultdict(int)
    top_mortality_causes = []
    mortality_data = MortalityForm.objects.all()

    for mortality in mortality_data:
        mortality_date = mortality.date
        year_month = mortality_date.strftime("%Y-%m")
        monthly_mortality_counts[year_month] += 1
        top_mortality_causes.append(mortality.cause)

    total_mortality_count = sum(monthly_mortality_counts.values())
    total_pig_count = sum(count for month, count in monthly_counts.items() if month not in monthly_sale_counts)
    mortality_rate = (total_mortality_count / total_pig_count) * 100
    current_year_month = date.today().strftime("%Y-%m")
    current_month_mortality_count = monthly_mortality_counts[current_year_month]
    current_month_pig_count = monthly_counts[current_year_month]
    average_monthly_mortality_rate = 0
    if current_month_pig_count != 0:
        average_monthly_mortality_rate += (current_month_mortality_count /current_month_pig_count) * 100
    else:
        messages.info(request, "no pigs registered for this month")
    # Count the number of vaccinated pigs
    all_vaccine_options = ["MH", "HPS", "PRRS", "PCV", "HCV1", "SIV", "APP", "HCV2", "PRV"]

    vaccinated_pigs = Pig.objects.annotate(vaccine_count=Count('vaccines__vaccine', distinct=True))

    for vaccine in all_vaccine_options:
        vaccinated_pigs = vaccinated_pigs.filter(vaccine_count__gte=1, vaccines__vaccine=vaccine)

    count_of_pigs_with_all_vaccines = vaccinated_pigs.count()
    print(count_of_pigs_with_all_vaccines)

    # Calculate the percentage of vaccinated pigs
    total_pigs = len(pig_data)
    total_pigs_exclude = Pig.objects.exclude(exclude_q).count()
    percentage_vaccinated = (count_of_pigs_with_all_vaccines / total_pigs) * 100
    vaccine_counts = Vaccine.objects.values('vaccine').annotate(count=Count('pig_id', distinct=True))
    vaccinated_per_vaccine_counts = Vaccine.objects.values('vaccine').annotate(count=Count('pig_id', distinct=True))
    vaccine_counts_dict = {option: 0 for option in all_vaccine_options}
    vaccine_needed = {}

    for entry in vaccinated_per_vaccine_counts:
        vaccine_counts_dict[entry['vaccine']] = entry['count']

    for option in all_vaccine_options:
        vaccinated_pigs_for_option = Vaccine.objects.filter(vaccine=option).count()
        # Exclude pigs that are sold or dead for the specific vaccine option
        vaccinated_pigs_for_option_excluding_sold_dead = vaccinated_pigs_for_option - Vaccine.objects.filter(
            Q(pig__pigsale__isnull=False, vaccine=option) | Q(pig__mortality_forms__isnull=False, vaccine=option)
        ).count()
        vaccine_needed[option] = total_pigs_exclude - vaccinated_pigs_for_option_excluding_sold_dead
        print(vaccine_needed)
    
    # Update counts based on available data
    unvaccinated_counts = {option: total_pigs - count for option, count in vaccine_counts_dict.items()}

    # Separate the dictionaries into lists for months and counts
    months, counts = zip(*monthly_counts.items())
    sale_months, sale_counts = zip(*monthly_sale_counts.items())
    mortality_dates, mortality_counts = zip(*monthly_mortality_counts.items())

    twenty_eight_days_ago = date.today() - timedelta(days=28)
    eighty_eight_days_ago = date.today() - timedelta(days=88)
    one_forty_eight_days_ago = date.today() - timedelta(days=148)
    pig_list_28_days = Pig.objects.filter(dob__gte=twenty_eight_days_ago).exclude(exclude_q).count() 
    pig_list_28_to_88_days = Pig.objects.filter(dob__gte=eighty_eight_days_ago, dob__lt=twenty_eight_days_ago).exclude(exclude_q).count() 
    pig_list_88_to_148_days = Pig.objects.filter(dob__gte=one_forty_eight_days_ago, dob__lt=eighty_eight_days_ago).exclude(exclude_q).count() 
    pig_list_greater_than_148_days = Pig.objects.filter(dob__lt=one_forty_eight_days_ago).exclude(exclude_q).count() 
    # Assuming your ration options are "Booster," "Starter," "Pre-Starter," and "Grower"

    # For Booster
    booster_option = "Booster"
    feed_stock_updates_booster = FeedStockUpdate.objects.filter(ration=booster_option)
    total_quantity_booster = FeedsInventory.objects.filter(feeds_ration=booster_option).aggregate(Sum('quantity'))['quantity__sum']
    total_quantity_booster = total_quantity_booster or 0
    # For Starter
    starter_option = "Starter"
    feed_stock_updates_starter = FeedStockUpdate.objects.filter(ration=starter_option)
    total_quantity_starter = FeedsInventory.objects.filter(feeds_ration=starter_option).aggregate(Sum('quantity'))['quantity__sum']
    total_quantity_starter = total_quantity_starter or 0
    # For Pre-Starter
    pre_starter_option = "Pre-Starter"
    feed_stock_updates_pre_starter = FeedStockUpdate.objects.filter(ration=pre_starter_option)
    total_quantity_pre_starter = FeedsInventory.objects.filter(feeds_ration=pre_starter_option).aggregate(Sum('quantity'))['quantity__sum']
    total_quantity_pre_starter = total_quantity_pre_starter or 0
    # For Grower
    grower_option = "Grower"
    feed_stock_updates_grower = FeedStockUpdate.objects.filter(ration=grower_option)
    total_quantity_grower = FeedsInventory.objects.filter(feeds_ration=grower_option).aggregate(Sum('quantity'))['quantity__sum']
    total_quantity_grower = total_quantity_grower or 0
    
    # Calculate the differences based on the specific ration options
    difference_booster = (total_quantity_booster - sum(feed_stock_update.count_update for feed_stock_update in feed_stock_updates_booster)) * 25
    difference_starter = (total_quantity_starter - sum(feed_stock_update.count_update for feed_stock_update in feed_stock_updates_starter))* 25
    difference_pre_starter = (total_quantity_pre_starter - sum(feed_stock_update.count_update for feed_stock_update in feed_stock_updates_pre_starter))* 25
    difference_grower = (total_quantity_grower - sum(feed_stock_update.count_update for feed_stock_update in feed_stock_updates_grower))* 25

    consumption_rate_suckling = 1.5
    consumption_rate_weanlings = 2.5
    consumption_rate_grower= 4
    consumption_rate_fattener= 6

    total_pigs_for_feeds= Pig.objects.exclude(exclude_q).count() 
    total_feed_needed_suckling = pig_list_28_days * consumption_rate_suckling * 30 
    total_feed_needed_weanling = pig_list_28_to_88_days * consumption_rate_weanlings*30
    total_feed_needed_grower = pig_list_88_to_148_days * consumption_rate_grower*30
    total_feed_needed_fattener = pig_list_greater_than_148_days * consumption_rate_fattener*30

    # You can round the result or format it as needed
    total_feed_suckling_formatted = "{:.2f}".format(total_feed_needed_suckling )
    total_feed_weanling_formatted = "{:.2f}".format(total_feed_needed_weanling )
    total_feed_grower_formatted = "{:.2f}".format(total_feed_needed_grower )
    total_feed_fattener_formatted = "{:.2f}".format(total_feed_needed_fattener)


   # Calculate the total_feed_needed_suckling_deficit
    total_feed_needed_suckling_deficit = max((pig_list_28_days * consumption_rate_suckling * 30) - difference_booster, 0)
    total_feed_needed_weanling_deficit = max((pig_list_28_to_88_days *  consumption_rate_weanlings * 30) - difference_pre_starter , 0)
    total_feed_needed_grower_deficit = max((pig_list_88_to_148_days * consumption_rate_grower * 30) -  difference_starter, 0)
    total_feed_needed_fattener_deficit = max((pig_list_greater_than_148_days * consumption_rate_fattener * 30) -  difference_grower, 0)

    # Format the deficit
    total_feed_suckling_deficit_formatted = "{:.2f}".format(total_feed_needed_suckling_deficit)
    total_feed_weanling_deficit_formatted = "{:.2f}".format(total_feed_needed_weanling_deficit)
    total_feed_grower_deficit_formatted = "{:.2f}".format(total_feed_needed_grower_deficit)
    total_feed_fattener_deficit_formatted = "{:.2f}".format(total_feed_needed_fattener_deficit)

    total_feed_needed_suckling_cost = total_feed_needed_suckling_deficit * 64
    total_feed_needed_weanling_cost = total_feed_needed_weanling_deficit * 44
    total_feed_needed_grower_cost =  total_feed_needed_grower_deficit * 30
    total_feed_needed_fattener_cost =  total_feed_needed_fattener_deficit * 28

    # Format the cost results
    total_feed_suckling_cost_formatted = "{:.2f}".format(total_feed_needed_suckling_cost)
    total_feed_weanling_cost_formatted = "{:.2f}".format(total_feed_needed_weanling_cost)
    total_feed_grower_cost_formatted = "{:.2f}".format(total_feed_needed_grower_cost)
    total_feed_fattener_cost_formatted = "{:.2f}".format(total_feed_needed_fattener_cost)


    weanlings_count = Pig.objects.filter(dob__gte=twenty_eight_days_ago).exclude(exclude_q).count()
    unique_weanling_ids = Weanling.objects.values('pig_id').annotate(count=Count('pig_id')).count()

    if weanlings_count < 500:
        weanlings_prescription = "The weanlings count is low. Consider adjusting feeding or housing conditions."
    else:
        weanlings_prescription = "The weanlings count is within an acceptable range."

    top_mortality_causes = [
        {'cause': cause, 'count': count}
        for cause, count in Counter(top_mortality_causes).most_common(5)
    ]
    current_year_month = date.today().strftime("%B %Y") 

    if average_monthly_mortality_rate > 5.0:
        prescription = "This month mortality rate is high. Consider improving health monitoring and biosecurity practices."
    else:
        prescription = "This month mortality rate is within an acceptable range."

    quantity_by_ration = FeedsInventory.objects.values('feeds_ration').annotate(total_quantity=Sum('quantity'))

    result = {}

    for item in quantity_by_ration:
        feeds_ration = item['feeds_ration']
        total_quantity = item['total_quantity']

        # Find the corresponding FeedStockUpdate records by feeds_ration
        feed_stock_updates = FeedStockUpdate.objects.filter(ration=feeds_ration)

        # Calculate the difference and store it in the result dictionary
        difference = total_quantity - sum(feed_stock_update.count_update for feed_stock_update in feed_stock_updates)
        result[feeds_ration] = difference

    threshold = 20  # Define your threshold here
    below_threshold_rations = {}

    for ration, difference in result.items():
        if difference < threshold:
            below_threshold_rations[ration] = difference

    # Now, create prescriptions for the rations that are below the threshold
    stock_prescriptions = []

    for ration, difference in below_threshold_rations.items():
        if difference <= 0:
            feeds_prescription = f"Warning! You have {difference} sacks of {ration} feeds.Order now!"
        else:
            feeds_prescription = f"Warning! You have {difference} remaining sacks of {ration} feeds, Consider ordering."

        stock_prescriptions.append(feeds_prescription)
    
    feed_expenses = FeedsInventory.objects.values('date').annotate(total_cost=Sum('cost'))
    dates = [item['date'].strftime('%Y-%m-%d') for item in feed_expenses]
    total_costs = [float(item['total_cost']) for item in feed_expenses]


    context = {
        "user_type": user_type,
        "months": json.dumps(list(months)),
        "counts": json.dumps(list(counts)),
        "sale_months": json.dumps(list(sale_months)),
        "sale_counts": json.dumps(list(sale_counts)),
        "pig_sales_monthly_data":json.dumps(list(pig_sales_monthly_data)),
        "mortality_dates": json.dumps(list(mortality_dates)),
        "mortality_counts": json.dumps(list(mortality_counts)),
        "percentage_vaccinated": percentage_vaccinated,
        "total_pigs": total_pigs,
        "count_of_pigs_with_all_vaccines": count_of_pigs_with_all_vaccines,
        "total_pigs_for_feeds":total_pigs_for_feeds,
        "total_feed_suckling_formatted":total_feed_suckling_formatted,
        "total_feed_weanling_formatted":total_feed_weanling_formatted,
        "total_feed_grower_formatted":total_feed_grower_formatted,
        "total_feed_fattener_formatted":total_feed_fattener_formatted,
        'pig_list_28_days': pig_list_28_days,
        'pig_list_28_to_88_days': pig_list_28_to_88_days,
        'pig_list_88_to_148_days': pig_list_88_to_148_days,
        'pig_list_greater_than_148_days': pig_list_greater_than_148_days,
        "mortality_rate": mortality_rate,
        "average_monthly_mortality_rate":average_monthly_mortality_rate,
        "top_mortality_causes": top_mortality_causes,
        "current_year_month": current_year_month,
        "prescription":prescription,
        "weanlings_count":weanlings_count,
        "unique_weanling_ids":unique_weanling_ids,
        "weanlings_prescription": weanlings_prescription,
        "average_weights": json.dumps(average_weights),
        'quantity_by_ration':quantity_by_ration,
        "result": result,
        "stock_prescriptions":stock_prescriptions, 
        "feed_expenses_dates": json.dumps(dates),
        "feed_expenses_costs": json.dumps(total_costs),
        'vaccine_needed': json.dumps(vaccine_needed),
        "vaccine_counts_dict":json.dumps(vaccine_counts_dict),
        "unvaccinated_counts": json.dumps(unvaccinated_counts),
        "total_feed_suckling_cost_formatted":total_feed_suckling_cost_formatted,
        "total_feed_weanling_cost_formatted":total_feed_weanling_cost_formatted,
        "total_feed_grower_cost_formatted":total_feed_grower_cost_formatted,
        "total_feed_fattener_cost_formatted":total_feed_fattener_cost_formatted,
        "difference_booster":difference_booster,
        "difference_starter":difference_starter,
        "difference_pre_starter": difference_pre_starter,
        "difference_grower":difference_grower,
        "total_feed_suckling_deficit_formatted":total_feed_suckling_deficit_formatted,
        "total_feed_weanling_deficit_formatted":total_feed_weanling_deficit_formatted,
        "total_feed_grower_deficit_formatted": total_feed_grower_deficit_formatted,
        "total_feed_fattener_deficit_formatted":total_feed_fattener_deficit_formatted,


    }

    return render(request, 'Farm/reports.html', context)



def data_entry(request, user_type):
    # Get a list of pig IDs that have a PigSale entry
    current_date = timezone.now().date()
    pig_sales_ids = PigSale.objects.values_list('pig_id', flat=True)
    weanling_pig_ids = Weanling.objects.values_list('pig_id', flat=True)

    # Use Q objects to filter out pigs that have either PigSale or MortalityForm
    excluded_pigs = Pig.objects.filter(Q(id__in=pig_sales_ids) | Q(mortality_forms__isnull=False))
    excluded_piglets = Pig.objects.filter(Q(id__in=pig_sales_ids) | Q(mortality_forms__isnull=False) | Q(id__in=weanling_pig_ids))
    # Exclude the excluded pigs from the list of all pigs
    sows = Sow.objects.all()
    pigs = Pig.objects.exclude(id__in=excluded_pigs)
    piglets = Pig.objects.exclude(id__in=excluded_piglets )

    return render(request, 'Farm/data_entry.html', {"user_type": user_type, 'pigs': pigs, 'pig_sales_ids': pig_sales_ids, 'sows':sows, 'piglets': piglets, 'date': current_date})



class LoginView(View):
    template_name = 'Authentication/Login.html'

    def get(self, request):
        # This handles the initial GET request to display the login form.
        return render(request, self.template_name, {"error_message": ""})

    def post(self, request):
        # This handles the POST request when the form is submitted.
        error_message = ""

        # Get the entered username and password from the form
        entered_username = request.POST.get("username")
        entered_password = request.POST.get("password")

        try:
            # Attempt to retrieve a user with the entered username from the database
            user = User.objects.get(username=entered_username)

            # Check if the entered password matches the stored password (in practice, use proper password hashing)
            if entered_password == user.password:
                # Successful login, set a user_type flag based on the role
                if user.role == 'administrator':
                    user_type = 'admin'
                else:
                    user_type = 'user'

                # Print the user_type for debugging
                print("user_type:", user_type)

                # Redirect to a page with the user_type parameter
                return redirect("Pigs", user_type=user_type)
            else:
                # Failed login, set the error message
                error_message = "Invalid password. Please try again."
        except User.DoesNotExist:
            # User with the entered username does not exist, set the error message
            error_message = "User not found. Please try again."

        # Render the login form with the error message
        return render(request, self.template_name, {"error_message": error_message})


from django.views.decorators.csrf import csrf_protect

@csrf_protect
def set_sched(request, user_type):
    if request.method == 'POST':
        # Handle form submission
        task_name = request.POST.get("taskname")
        due_date = request.POST.get("duedate")
        due_time = request.POST.get("duetime")
        description = request.POST.get("desc")
        is_done = request.POST.get("is_done")

        # Convert "on" to True and None to False for is_done
        is_done = is_done == "on"

        # If a task name is provided, create a new Task object and save it to the database
        if task_name:
            task = Task(task_name=task_name, due_date=due_date, due_time=due_time, description=description, is_done=is_done)
            task.save()

            # Redirect to the same page to prevent form resubmission
            return redirect('set_sched', user_type=user_type)

    # Retrieve tasks
    all_tasks = Task.objects.all()
    today = date.today()
    today_tasks = Task.objects.filter(due_date=today)
    sow_list = Sow.objects.all()

    # Filter tasks based on their is_done field
    todo_tasks = all_tasks.filter(is_done=False)
    done_tasks = all_tasks.filter(is_done=True)

    return render(request, "Farm/set_sched.html", {"today_tasks": today_tasks, "todo_tasks": todo_tasks, "done_tasks": done_tasks, "user_type": user_type, "sow_list":sow_list})



def get_checkbox_states(request):
    # Assuming you have a model called Task with an is_done field
    tasks = Task.objects.all()

    # Create a list to store the checkbox states
    checkbox_states = [{'id': task.id, 'is_done': task.is_done} for task in tasks]

    # Debugging statement to check the data before returning
    print("Checkbox States:", checkbox_states)

    # Return the checkbox states as a JSON response with safe=False
    return JsonResponse(checkbox_states, safe=False)


def update_task_status(request):
    if request.method == 'POST':
        task_id = request.POST.get('task_id')
        is_done = request.POST.get('is_done')

        try:
            task = Task.objects.get(id=task_id)
            task.is_done = is_done == 'true'  # Convert the string to a boolean
            task.save()

            # Prepare the task data to include in the response
            task_data = {
                'id': task.id,
                'task_name': task.task_name,
                'is_done': task.is_done,
                # Include any other task-related data you need
            }

            return JsonResponse({'message': 'Task status updated successfully', 'task': task_data})
        except Task.DoesNotExist:
            return JsonResponse({'error': 'Task not found'}, status=404)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=400)
    

def tasks_for_date(request, selected_date):
    # Replace 'Task' with your actual Task model and 'due_date' with the appropriate field name
    tasks_for_selected_date = Task.objects.filter(due_date=selected_date)

    # Format the tasks data as a list of dictionaries
    tasks_data = [
        {
            'id': task.id,
            'task_name': task.task_name,
            'is_done': task.is_done,
            # Include other task data as needed
        }
        for task in tasks_for_selected_date
    ]

    # Return the tasks data as JSON response
    return JsonResponse(tasks_data, safe=False)

def delete_user(request, user_type):
    if request.method == 'POST':
        user_id = request.POST.get('id')
        try:
            user = User.objects.get(pk=user_id)
            user.delete()
            return JsonResponse({'success': True})
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User not found'})
    return render(request, 'Farm/manage_user.html', { "user_type": user_type, })


def update_user(request, user_type):
    if request.method == 'POST':
        data = request.POST  # Access POST data directly
        user_id = data.get('id')  # Get the user ID from POST data

        try:
            with transaction.atomic():
                user = User.objects.get(pk=user_id)
                user.username = data.get('username')
                user.firstname = data.get('firstname')
                user.lastname = data.get('lastname')
                user.role = data.get('role')
                user.date = data.get('date')
                user.save()

            # Debug: Add print statements or use Django's logging
            print("User updated successfully.")
            
            return JsonResponse({'success': True, 'updated_user': {
                'firstname': user.firstname,
                'lastname': user.lastname,
                'username': user.username,
                'role': user.role,
                'date': user.date,
            }})
        except User.DoesNotExist:
            # Debug: Print error message
            print("User not found.")
            
            return JsonResponse({'success': False, 'error': 'User not found'})
        except Exception as e:
            # Debug: Print error message
            print(f"Error: {str(e)}")
            
            return JsonResponse({'success': False, 'error': str(e)})

    return render(request, 'Farm/manage_user.html', {"user_type": user_type})


def delete_pig(request, user_type, pig_id):
    if request.method == 'POST':
        try:
            pig = Pig.objects.get(id=pig_id)
            pig.delete()
            return JsonResponse({'success': True})
        except Pig.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Pig not found'})

    return JsonResponse({'success': False, 'error': 'Invalid request method'})

def get_pig_data(request, pig_id):
    try:
        # Retrieve the pig data based on pig_id
        pig = Pig.objects.get(pk=pig_id)
        print(len(pig.barcode_image)) 
        # Serialize the pig data into a dictionary
        pig_data = {
            'pig_id': pig.pig_id,
            'dam': pig.dam,
            'dob': pig.dob.strftime('%Y-%m-%d'),  # Format date as string
            'sire': pig.sire,
            'pig_class': pig.pig_class,
            'sex': pig.sex,
            'count': pig.count,
            'weight': str(pig.weight),  # Convert DecimalField to string
            'remarks': pig.remarks,
            'barcode_image': base64.b64encode(pig.barcode_image.tobytes()).decode()
            # Add more fields as needed
        }
        
        return JsonResponse({'success': True, 'pig_data': pig_data})
    except Pig.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Pig not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
    
def update_pig(request, pig_id, user_type):
    if request.method == 'POST':
        data = request.POST  # Access POST data directly

        try:
            with transaction.atomic():
                # Get the pig using the provided pig_id
                pig = Pig.objects.get(pk=pig_id)
                # Update pig data fields based on your form field names
                pig.dam = data.get('dam')
                pig.dob = data.get('dob')
                pig.sire = data.get('sire')
                pig.pig_class = data.get('pig_class')
                pig.sex = data.get('sex')
                pig.count = data.get('count')
                pig.weight = data.get('weight')
                pig.remarks = data.get('remarks')
                # Add more fields as needed
                pig.save()

            # Debug: Add print statements or use Django's logging
            print("Pig updated successfully.")

            # Prepare the updated pig data as a dictionary
            updated_pig_data = {
                'pig_id': pig.pig_id,
                'dam': pig.dam,
                'dob': pig.dob,  # No need for strftime if dob is already in the desired format
                'sire': pig.sire,
                'pig_class': pig.pig_class,
                'sex': pig.sex,
                'count': pig.count,
                'weight': str(pig.weight),  # Convert DecimalField to string
                'remarks': pig.remarks,
                # Add more fields as needed
            }

            return JsonResponse({'success': True, 'updated_pig_data': updated_pig_data})
        except Pig.DoesNotExist:
            # Debug: Print error message
            print("Pig not found.")

            return JsonResponse({'success': False, 'error': 'Pig not found'})
        except Exception as e:
            # Debug: Print error message
            print(f"Error: {str(e)}")

            return JsonResponse({'success': False, 'error': str(e)})

    return render(request, 'Farm/add_pigs.html', {"user_type": user_type})


def add_sow(request, user_type):
    context = {
        'user_type': user_type,
    }

    if request.method == 'POST':
        # Handle form submission
        pig_id = request.POST.get("pig_id")
        dam = request.POST.get("dam")
        dob = request.POST.get("dob")
        sire = request.POST.get("sire")
        pig_class = request.POST.get("pig_class")
        sex = request.POST.get("sex")
        count = request.POST.get("count")
        weight = request.POST.get("weight")
        remarks = request.POST.get("remarks")
        verif_by = request.POST.get("verif_by")
        birthdate = request.POST.get("date")

        try:
            count = int(count)
            weight = float(weight)
        except (ValueError, TypeError):
            pass

        sow = Sow(
            pig_id=pig_id,
            dam=dam,
            dob=dob,
            sire=sire,
            pig_class=pig_class,
            sex=sex,
            count=count,
            weight=weight,
            remarks=remarks,
            verif_by=verif_by,
            date=birthdate
        )
        sow.save()

        sow_list = Sow.objects.all()

        context['sow_list'] = sow_list
        return redirect('Add_Pigs', user_type=user_type)

    return render(request, 'Farm/add_pigs.html', context)

def delete_sow(request, user_type, sow_id):
    if request.method == 'POST':
        try:
            sow = Sow.objects.get(id=sow_id)  # Get the sow object by ID
            sow.delete()
            return JsonResponse({'success': True})
        except Sow.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Sow not found'})

    return JsonResponse({'success': False, 'error': 'Invalid request method'})

def get_sow_data(request, pig_id):
    try:
        sow = Sow.objects.get(pk=pig_id)
        
        # Serialize the sow data into a dictionary
        sow_data = {
            'pk': sow.pk,
            'sow_id': sow.pig_id,
            'dam': sow.dam,
            'dob': sow.dob.strftime('%Y-%m-%d'),  # Format date as string
            'sire': sow.sire,
            'pig_class': sow.pig_class,
            'sex': sow.sex,
            'count': sow.count,
            'weight': str(sow.weight),  # Convert DecimalField to string
            'remarks': sow.remarks,
            # Add more fields as needed
        }
        
        return JsonResponse({'success': True, 'sow_data': sow_data})
    except Sow.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Sow not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
    
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render
from .models import Sow
def update_sow_data(request, pig_id, user_type):
    if request.method == 'POST':
        data = request.POST  
        
        try:
            with transaction.atomic():
                # Get the sow using the provided primary key (pk)
                sow = Sow.objects.get(pk=pig_id)
                
                # Update sow data fields based on your form field names
                sow.dam = data.get('edit_sow_dam')
                sow.dob = data.get('edit_sow_dob')
                sow.sire = data.get('edit_sow_sire')
                sow.pig_class = data.get('edit_sow_pig_class')
                sow.sex = data.get('edit_sow_sex')
                sow.count = data.get('edit_sow_count')
                sow.weight = data.get('edit_sow_weight')
                sow.remarks = data.get('edit_sow_remarks')
                # Add more fields as needed
                sow.save()

            # Debug: Add print statements or use Django's logging
            print("Sow updated successfully")
            return redirect('Add_Pigs', user_type=user_type)

        except Sow.DoesNotExist:
            # Debug: Print error message
            print("Sow not found.")
            return JsonResponse({'success': False, 'error': 'Sow not found'})

        except Exception as e:
            # Debug: Print error message
            print(f"Error: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)})

    return render(request, 'Farm/add_pigs.html', {"user_type": user_type})

  
def save_feeds_inventory(request, user_type):
    if request.method == 'POST':
        feeds_brand = request.POST.get('feedsB')
        feeds_ration = request.POST.get('feedsR')
        cost = request.POST.get('cost')
        quantity = request.POST.get('quantity')
        verified_by = request.POST.get('verifBy')
        date = request.POST.get('date')

        feeds_inventory = FeedsInventory(
            feeds_brand=feeds_brand,
            feeds_ration=feeds_ration,
            cost=cost,
            quantity=quantity,
            verified_by=verified_by,
            date=date
        )
        feeds_inventory.save()
        messages.success(request, 'Feeds Stock Added to the database')
        return render(request, 'Farm/success_overlay.html', {'user_type': user_type})

    return render(request, 'Farm/data_entry.html', {"user_type": user_type})

def add_feed_stock_update(request, user_type):
    if request.method == 'POST':
        ration = request.POST.get('ration')
        count_update = request.POST.get('count_update')
        date = request.POST.get('date')
        verify_by = request.POST.get('verify_by')


        feed_stock_update = FeedStockUpdate(
            ration=ration, 
            count_update=count_update,
            date=date,
            verify_by=verify_by
        )
        feed_stock_update.save()

        messages.success(request, 'Feeds Stock Updated')
        return render(request, 'Farm/success_overlay2.html', {'user_type': user_type})

    return render(request, 'Farm/data_entry.html', {"user_type": user_type})

def save_pig_sale(request, user_type):
    if request.method == 'POST':
        pig_id = request.POST.get('PigID')
        weight = request.POST.get('weight')
        price = request.POST.get('price')
        verif_by = request.POST.get('Verified')
        date = request.POST.get('date')

        # Get the selected pig object
        pig = Pig.objects.get(id=pig_id)

        # Create a PigSale object
        pig_sale = PigSale(
            pig=pig,
            weight=weight,
            price=price,
            verif_by=verif_by,
            date=date
        )
        pig_sale.save()
        messages.success(request, 'Pig sale added to database')
        return render(request, 'Farm/success_overlay.html', {'user_type': user_type})
    
    # Pig sales IDs can be accessed from the context
    pig_sales_ids = PigSale.objects.values_list('pig_id', flat=True)
    pigs = Pig.objects.exclude(id__in=pig_sales_ids)

    return render(request, 'Farm/data_entry.html', {'pigs': pigs, 'pig_sales_ids': pig_sales_ids})

def mortality_form(request, user_type):
    if request.method == 'POST':
        pig_id = request.POST.get('pig_id')
        date = request.POST.get('date')
        pig_class = request.POST.get('class')
        cause = request.POST.get('cause')
        location = request.POST.get('location')
        remarks = request.POST.get('remarks')
        reported_by = request.POST.get('repBy')
        verified_by = request.POST.get('verifBy')

        # Check if the selected pig is not sold
        if not PigSale.objects.filter(pig_id=pig_id).exists():
            mortality_form = MortalityForm(
                pig_id=pig_id,
                date=date,
                pig_class=pig_class,
                cause=cause,
                location=location,
                remarks=remarks,
                reported_by=reported_by,
                verified_by=verified_by
            )
            mortality_form.save()
            messages.success(request, 'Mortality Form Saved')
            return render(request, 'Farm/success_overlay.html', {'user_type': user_type})
        else:
 
            error_message = "Selected pig has been sold."

    context = {
        'user_type': user_type,
    }

    if 'error_message' in locals():
        context['error_message'] = error_message

    return render(request, 'Farm/data_entry.html', context)

from .models import Pig, Vaccine

def save_vaccine(request, user_type):
    if request.method == 'POST':
        pig_id = request.POST.get('pig_id')
        date = request.POST.get('date')
        vaccine = request.POST.get('vaccine')
        purpose = request.POST.get('purpose')
        dosage = request.POST.get('dosage')

        # Find the pig based on the pig ID
        try:
            pig = Pig.objects.get(id=pig_id)
            vaccine_record = Vaccine(pig=pig, date=date, vaccine=vaccine, purpose=purpose, dosage=dosage)
            vaccine_record.save()
            # Redirect to a success page or do something else
            messages.success(request, 'Pig vaccinated successfully!')
            return render(request, 'Farm/success_overlay.html', {'user_type': user_type})
        except Pig.DoesNotExist:
            error_message = "Pig with the provided ID does not exist."

    context = {
        'user_type': user_type,
    }

    if 'error_message' in locals():
        context['error_message'] = error_message

    return render(request, 'Farm/data_entry.html', context)

from .models import Weanling


def save_weanling(request, user_type):
    if request.method == 'POST':
        pig_id = request.POST.get('pig_id')
        date = request.POST.get('date')
        sow_id = request.POST.get('sow_id')
        weight = request.POST.get('weight')
        sex = request.POST.get('sex')
        remarks = request.POST.get('remarks')

        weanling = Weanling(
            pig_id=pig_id,
            date=date,
            sow_id=sow_id,
            weight=weight,
            sex=sex,
            remarks=remarks,
        )
        weanling.save()

        messages.success(request, 'Weanling Form Saved')
        return render(request, 'Farm/success_overlay.html', {'user_type': user_type})

    return render(request, 'Farm/data_entry.html')

def add_sp(request, user_type):
    if request.method == 'POST':
        sow_no = request.POST.get('SowNo')
        dam = request.POST.get('dam')
        dob = request.POST.get('dob')
        sire = request.POST.get('sire')
        pig_class = request.POST.get('pig_class')
        parity = request.POST.get('parity')
        
        first_boar = request.POST.get('first')
        second_boar = request.POST.get('second')
        third_boar = request.POST.get('third')
        date_bred = request.POST.get('bred')
        date_due = request.POST.get('due')
        date_farr = request.POST.get('farr')

        alive = request.POST.get('alive')
        mk = request.POST.get('mk')
        sb = request.POST.get('SB')
        mffd = request.POST.get('mffd')
        total_litter_size = request.POST.get('totalLS')
        ave_litter_size = request.POST.get('aveLS')

        date_weaned = request.POST.get('dateW')
        no_weaned = request.POST.get('noW')
        total_weaned = request.POST.get('totalW')
        ave_weaned = request.POST.get('aveW')
        total_kilo_weaned = request.POST.get('totalKW')

        # Get the selected pig object
        sow = Sow.objects.get(id=sow_no)

        sp = SowPerformance(
            sow_no = sow,
            dam = dam,
            dob = dob,
            sire = sire,
            pig_class = pig_class,
            pig_parity = parity,

            first_boar = first_boar,
            second_boar = second_boar,
            third_boar = third_boar,
            date_bred = date_bred,
            date_due = date_due,
            date_farr = date_farr,

            alive = alive,
            mk = mk,
            sb = sb,
            mffd = mffd,
            total_litter_size = total_litter_size,
            ave_litter_size = ave_litter_size,

            date_weaned = date_weaned,
            no_weaned = no_weaned,
            total_weaned = total_weaned,
            ave_weaned = ave_weaned,
            total_kilo_weaned = total_kilo_weaned
        )
        sp.save()
        messages.success(request, 'Sow Performance added to database')
        return render(request, 'Farm/success_overlay.html', {'user_type': user_type})
    
    # Sow Performance IDs can be accessed from the context
    sow_perf_ids = SowPerformance.objects.values_list('pig_id', flat=True)
    sows = Sow.objects.get.all(id__in=sow_perf_ids)

    return render(request, 'Farm/data_entry.html', {'sows': sows, 'sow_perf_ids': sow_perf_ids})

def search_suggestions(request):
    search_query = request.GET.get('search_query', '')

    # Search for pig_id in the Pig model, excluding those with PigSale or MortalityForm
    pig_results = Pig.objects.filter(pig_id__icontains=search_query).exclude(
        Q(pigsale__isnull=False) | Q(mortality_forms__isnull=False)
    ).values('pig_id')

    # Extract pig_id values
    suggestions = [result['pig_id'] for result in pig_results]

    return JsonResponse({'suggestions': suggestions})

def search_sow_suggestions(request):
    search_query = request.GET.get('search_query', '')

    # Search for pig_id in the Sow model and fetch both pig_id and pk
    sow_results = Sow.objects.filter(pig_id__icontains=search_query).values('pk', 'pig_id')

    # Extract pig_id and pk values
    suggestions = list(sow_results)

    return JsonResponse({'suggestions': suggestions})

def get_sow_performance_data(request, pig_id):
    
    try:
        sow = Sow.objects.get(pk=pig_id)
        sow_performances = SowPerformance.objects.filter(sow_no=sow)
        
        if sow_performances:
            # Create a list to store sow performance data for all records
            sow_perf_data_list = []
            
            for sow_performance in sow_performances:
                sow_perf_data = {
                    'id': sow_performance.id,
                    'pig_id': sow.pig_id, 
                    'dam': sow_performance.dam,
                    'dob': sow_performance.dob,
                    'sire': sow_performance.sire,
                    'pig_class': sow_performance.pig_class,
                    'pig_parity': sow_performance.pig_parity,
                    'first_boar': sow_performance.first_boar,
                    'second_boar': sow_performance.second_boar,
                    'third_boar': sow_performance.third_boar,
                    'date_bred': sow_performance.date_bred.strftime('%Y-%m-%d'),
                    'date_due': sow_performance.date_due.strftime('%Y-%m-%d'),
                    'date_farr': sow_performance.date_farr.strftime('%Y-%m-%d'),
                    'alive': sow_performance.alive,
                    'mk': sow_performance.mk,
                    'sb': sow_performance.sb,
                    'mffd': sow_performance.mffd,
                    'total_litter_size': sow_performance.total_litter_size,
                    'ave_litter_size': sow_performance.ave_litter_size,
                    'date_weaned': sow_performance.date_weaned.strftime('%Y-%m-%d'),
                    'no_weaned': sow_performance.no_weaned,
                    'total_weaned': sow_performance.total_weaned,
                    'ave_weaned': sow_performance.ave_weaned,
                    'total_kilo_weaned': sow_performance.total_kilo_weaned,
                    # Add more fields as needed
                }
                sow_perf_data_list.append(sow_perf_data)
            
            return JsonResponse({'success': True, 'sow_perf_data_list': sow_perf_data_list})
        else:
            return JsonResponse({'success': False, 'error': 'Sow Performance data not found'})
    except Sow.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Sow not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def archive_user(request, user_id):
    if request.method == 'POST':
        # Retrieve the user with the given user_id (you can use get_object_or_404 or similar)
        user = User.objects.get(pk=user_id)

        # Perform the archive action by setting the archive_user field to True
        user.archive_user = True
        user.save()

        # You can return a JSON response to confirm the successful archive
        return JsonResponse({'message': 'User archived successfully'})

    # Handle other HTTP methods if needed
    return JsonResponse({'message': 'Invalid request method'}, status=400)

def get_vaccine_data(request, pig_id):
    # Query the Vaccine model to get vaccine data for the pig with the given ID
    vaccines = Vaccine.objects.filter(pig__pig_id=pig_id)
    
    # Serialize the vaccine data as a list of dictionaries
    vaccine_data = [
        {
            'date': vaccine.date,
            'vaccine': vaccine.vaccine,
            'purpose': vaccine.purpose,
            'dosage': vaccine.dosage,
        }
        for vaccine in vaccines
    ]

    return JsonResponse({'vaccine_data': vaccine_data})
    
def generate_sales_report(request):
    if request.method == 'POST':
        # Get selected month and year from the form
        selected_month = request.POST.get('month')
        selected_year = request.POST.get('year')
        
        # Example: Check if the selected values are correct (you can add more validation)
        if selected_month and selected_year:
            # Filter PigSales for the selected month and year
            sales_data = PigSale.objects.filter(date__year=selected_year, date__month=selected_month)

            # Create a buffer for the PDF
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)

            elements = []

            # Create a custom title style
            title_style = ParagraphStyle(
                name='CustomTitleStyle',
                fontSize=14,
                textColor='black',
                alignment=1,
            )
            styles = getSampleStyleSheet()["Heading3"]
            heading = getSampleStyleSheet()["Heading2"]

            # Create a title for the report using the custom style
            elements.append(Paragraph("GOODWILL AGRO INDUSTRIAL DEVELOPMENT CORPORATION", style=heading))
            selected_date = datetime(int(selected_year), int(selected_month), 1)
            elements.append(Paragraph("Sales Report for {}".format(selected_date.strftime('%Y-%B')), style=title_style))
            elements.append(Spacer(1, 12))

            # Define the data for the table
            table_data = [['Pig ID', 'Weight', 'Price', 'Date']]

            total_sales = Decimal(0)
            total_count = 0
            weights = []

            for sale in sales_data:
                table_data.append([sale.pig.pig_id, sale.weight, sale.price, sale.date])
                total_sales += sale.price
                total_count += 1
                weights.append(sale.weight)

            average_weight = mean(weights) if weights else 0

            # Add a summary section
            elements.append(Paragraph("Total Sales: Php {:.2f}".format(total_sales), style=styles))
            elements.append(Paragraph("Total Count: {}".format(total_count), style=styles))
            elements.append(Paragraph("Average Weight: {:.2f}".format(average_weight), style=styles))

            # Create a table
            table = Table(table_data, colWidths=120, rowHeights=30)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.white),
            ]))

            elements.append(table)
            elements.append(Spacer(1, 12))

            # Build the PDF document
            doc.build(elements)
            buffer.seek(0)

            # Create a response with the PDF file
            response = FileResponse(buffer, as_attachment=True, filename="sales_report.pdf")
            return response

    return render(request, 'your_template.html')

def generate_mortality_report(request):
    if request.method == 'POST':
        # Get the selected month and year from the form
        selected_month = int(request.POST.get('month'))
        selected_year = int(request.POST.get('year'))

        # Filter MortalityForm based on the selected month and year
        moratlity_data = MortalityForm.objects.filter(date__year=selected_year, date__month=selected_month)

        # Create a buffer for the PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)

        elements = []

        # Create a custom title style
        title_style = ParagraphStyle(
            name='CustomTitleStyle',
            fontSize=14,
            textColor='black',  # Change the title text color
            alignment=1,  # Center alignment
        )
        styles = getSampleStyleSheet()["Heading3"]
        heading = getSampleStyleSheet()["Heading2"]

        total_mortality = 0
        top_cause = MortalityForm.objects.filter(date__year=selected_year, date__month=selected_month).aggregate(max_value=Max('cause'))['max_value']

        # Create a title for the report using the custom style
        selected_date = datetime(int(selected_year), int(selected_month), 1)
        elements.append(Paragraph("GOODWILL AGRO INDUSTRIAL DEVELOPMENT CORPORATION", style=heading))
        elements.append(Paragraph("Mortality Report for " + selected_date.strftime('%Y-%B'), style=title_style))
        elements.append(Spacer(1, 12))

        # Define the data for the table
        table_data = [['', 'Pig ID', 'Cause', 'Location', 'Date']]

        for mortality in moratlity_data:
            table_data.append([mortality.id, mortality.pig_id, mortality.cause, mortality.location, mortality.date])
            total_mortality += 1

        # Add a summary section
        elements.append(Paragraph("Total Mortality: %d" % total_mortality, style=styles))
        elements.append(Paragraph("Top Cause: %s" % top_cause, style=styles))

        # Create a table
        table = Table(table_data, colWidths=100, rowHeights=30)
        table.setStyle(TableStyle([
            ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.white),
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.white),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 12))

        # Build the PDF document
        doc.build(elements)
        buffer.seek(0)

        # Create a response with the PDF file
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="mortality_report.pdf"'
        response.write(buffer.getvalue())
        return response

    return render(request, 'your_form_template.html')

def generate_weanling_report(request):
    if request.method == 'POST':
        # Get the selected month and year from the form
        selected_month = int(request.POST.get('month'))
        selected_year = int(request.POST.get('year'))

        # Filter Weanling based on the selected month and year
        weanling_data = Weanling.objects.filter(date__year=selected_year, date__month=selected_month)
        
        # Filter recent pigs for the selected month and year
        recent_pigs = Pig.objects.filter(date__year=selected_year, date__month=selected_month)
        recent_pigs_total = len(recent_pigs)

        # Create a buffer for the PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)

        total_weanling_count = 0
        elements = []

        # Create a custom title style
        title_style = ParagraphStyle(
            name='CustomTitleStyle',
            fontSize=14,
            textColor='black',  # Change the title text color
            alignment=1,  # Center alignment
        )
        styles = getSampleStyleSheet()["Heading3"]
        heading = getSampleStyleSheet()["Heading2"]

        # Create a title for the report using the custom style
        selected_date = datetime(int(selected_year), int(selected_month), 1)
        elements.append(Paragraph("GOODWILL AGRO INDUSTRIAL DEVELOPMENT CORPORATION", style=heading))
        elements.append(Paragraph("Weanling Report for " + selected_date.strftime('%Y-%B'), style=title_style))
        elements.append(Spacer(1, 12))

        # Define the data for the table
        table_data = [['', 'Pig ID', 'Date']]

        for weanling in weanling_data:
            table_data.append([weanling.id, weanling.pig_id, weanling.date])
            total_weanling_count += 1

        wean_pct = 0
        if recent_pigs_total != 0:
            wean_pct += (total_weanling_count / recent_pigs_total) * 100
        else:
            messages.info(request, "No pigs to wean yet")

        elements.append(Paragraph("Total Weanling Count: %d" % total_weanling_count, style=styles))
        elements.append(Paragraph("Total Percentage: %d" % wean_pct + "%", style=styles))

        # Create a table
        table = Table(table_data, colWidths=130, rowHeights=30)
        table.setStyle(TableStyle([
            ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.white),
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.white),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 12))

        # Build the PDF document
        doc.build(elements)
        buffer.seek(0)

        # Create a response with the PDF file
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="weanling_report.pdf"'
        response.write(buffer.getvalue())
        return response

    return render(request, 'your_form_template.html')
       
def generate_vaxx_report(request):
    # Get the current month and year
    current_month = datetime.now()

    pig_data = Pig.objects.filter(date__year=current_month.year, date__month=current_month.month)
    total_pigs = len(pig_data)
    mh_count = "MH"
    mh_vaxx = Vaccine.objects.filter(vaccine = mh_count).filter(date__year=current_month.year, date__month=current_month.month).count()
    mh_pct = 0
    if total_pigs != 0:
        mh_pct += 100 * (mh_vaxx / total_pigs)
    else: 
        messages.info(request, "No Pigs Registered this Month yet")
    hps_count = "HPS"
    hps_vaxx = Vaccine.objects.filter(vaccine = hps_count).filter(date__year=current_month.year, date__month=current_month.month).count()
    hps_pct = 0
    if total_pigs != 0:
        hps_pct += 100 * (hps_vaxx / total_pigs)
    else: 
        messages.info(request, "No Pigs Registered this Month yet")
    prrs_count = "PRRS"
    prrs_vaxx = Vaccine.objects.filter(vaccine = prrs_count).filter(date__year=current_month.year, date__month=current_month.month).count()
    prrs_pct = 0
    if total_pigs != 0:
        prrs_pct += 100 * (prrs_vaxx / total_pigs)
    else: 
        messages.info(request, "No Pigs Registered this Month yet")
    pcv_count = "PCV"
    pcv_vaxx = Vaccine.objects.filter(vaccine = pcv_count).filter(date__year=current_month.year, date__month=current_month.month).count()
    pcv_pct = 0
    if total_pigs != 0:
        pcv_pct += 100 * (pcv_vaxx / total_pigs)
    else: 
        messages.info(request, "No Pigs Registered this Month yet")
    prv_count = "PRV"
    prv_vaxx = Vaccine.objects.filter(vaccine = prv_count).filter(date__year=current_month.year, date__month=current_month.month).count()
    prv_pct = 0
    if total_pigs != 0:
        prv_pct += 100 * (prv_vaxx / total_pigs)
    else: 
        messages.info(request, "No Pigs Registered this Month yet")
    hcv1_count = "HCV1"
    hcv1_vaxx = Vaccine.objects.filter(vaccine = hcv1_count).filter(date__year=current_month.year, date__month=current_month.month).count()
    hcv1_pct = 0
    if total_pigs != 0:
        hcv1_pct += 100 * (hcv1_vaxx / total_pigs)
    else: 
        messages.info(request, "No Pigs Registered this Month yet")
    hcv2_count = "HCV2"
    hcv2_vaxx = Vaccine.objects.filter(vaccine = hcv2_count).filter(date__year=current_month.year, date__month=current_month.month).count()
    hcv2_pct = 0
    if total_pigs != 0:
        hcv2_pct += 100 * (hcv2_vaxx / total_pigs)
    else: 
        messages.info(request, "No Pigs Registered this Month yet")
    siv_count = "SIV"
    siv_vaxx = Vaccine.objects.filter(vaccine = siv_count).filter(date__year=current_month.year, date__month=current_month.month).count()
    siv_pct = 0
    if total_pigs != 0:
        siv_pct += 100 * (siv_vaxx / total_pigs)
    else: 
        messages.info(request, "No Pigs Registered this Month yet")
    app_count = "APP"
    app_vaxx = Vaccine.objects.filter(vaccine = app_count).filter(date__year=current_month.year, date__month=current_month.month).count()
    app_pct = 0
    if total_pigs != 0:
        app_pct += 100 * (mh_vaxx / total_pigs)
    else: 
        messages.info(request, "No Pigs Registered this Month yet")

    # Create a buffer for the PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)

    elements = []

    # Create a custom title style
    title_style = ParagraphStyle(
        name='CustomTitleStyle',
        fontSize=14,
        textColor='black',  # Change the title text color
        alignment=1,  # Center alignment
    )
    styles = getSampleStyleSheet()["Heading3"]
    heading = getSampleStyleSheet()["Heading2"]

    # Create a title for the report using the custom style
    elements.append(Paragraph("GOODWILL AGRO INDUSTRIAL DEVELOPMENT CORPORATION", style=heading))
    elements.append(Paragraph("Vaccine Report for " + current_month.strftime('%Y-%B'), style=title_style))
    elements.append(Spacer(1, 12))

    # Define the data for the table
    table_data = [['Vaccine', 'Vaccinated Pigs', 'Percentage']]

    table_data.append(["MH", mh_vaxx, "%.2f" % mh_pct + "%"])
    table_data.append(["HPS", hps_vaxx, "%.2f" % hps_pct + "%"])
    table_data.append(["PRRS", prrs_vaxx, "%.2f" % prrs_pct + "%"])
    table_data.append(["PCV", pcv_vaxx, "%.2f" % pcv_pct + "%"])
    table_data.append(["PRV", prv_vaxx, "%.2f" % prv_pct + "%"])
    table_data.append(["HCV1", hcv1_vaxx, "%.2f" % hcv1_pct + "%"])
    table_data.append(["HCV2", hcv2_vaxx, "%.2f" % hcv2_pct + "%"])
    table_data.append(["SIV", siv_vaxx, "%.2f" % siv_pct + "%"])
    table_data.append(["APP", app_vaxx, "%.2f" % app_pct + "%"])

    # Create a table
    table = Table(table_data, colWidths=130, rowHeights=30)
    table.setStyle(TableStyle([
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.white),
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.white),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 12))

    # Build the PDF document
    doc.build(elements)
    buffer.seek(0)

    # Create a response with the PDF file
    response = FileResponse(buffer, as_attachment=True, filename="vaxx_report.pdf")

    if request.method == 'POST':
        return response
    
def generate_feed_report(request):
    # Get the current month and year
    current_month = datetime.now()
    
    quantity_by_ration = FeedsInventory.objects.values('feeds_ration').annotate(total_quantity=Sum('quantity'))
    consumption_by_ration = FeedStockUpdate.objects.values('ration').annotate(total_consumption=Sum('count_update'))

    result = {}

    # Calculate the difference for each feeds_ration
    for item in quantity_by_ration:
        feeds_ration = item['feeds_ration']
        total_quantity = item['total_quantity']

        consumption_item = next((consumption for consumption in consumption_by_ration if consumption['ration'] == feeds_ration), None)
        total_consumption = consumption_item['total_consumption'] if consumption_item else 0

        difference = total_quantity - total_consumption
        result[feeds_ration] = difference

# Now you have the result dictionary with the differences for each feeds_ration

    # Create a buffer for the PDF

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)

    elements = []

    # Create a custom title style
    title_style = ParagraphStyle(
        name='CustomTitleStyle',
        fontSize=14,
        textColor='black',  # Change the title text color
        alignment=1,  # Center alignment
    )
    styles = getSampleStyleSheet()["Heading3"]
    heading = getSampleStyleSheet()["Heading2"]

    # Create a title for the report using the custom style
    elements.append(Paragraph("GOODWILL AGRO INDUSTRIAL DEVELOPMENT CORPORATION", style=heading))
    elements.append(Paragraph("Feeds Report for " + current_month.strftime('%Y-%B'), style=title_style))
    elements.append(Spacer(1, 12))

    # Define the data for the table
   # Define the data for the table
    table_data = [['Ration Type', 'Initial Quantity', 'Consumption', 'Available Stocks']]

    for ration_type, difference in result.items():
        initial_quantity = quantity_by_ration.get(feeds_ration=ration_type)['total_quantity']
        consumption = initial_quantity - difference
        table_data.append([ration_type, initial_quantity, consumption, difference])


# Create a table
    table = Table(table_data, colWidths=130, rowHeights=30)
    table.setStyle(TableStyle([
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.white),
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.white),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 12))

    # Build the PDF document
    doc.build(elements)
    buffer.seek(0)

    # Create a response with the PDF file
    response = FileResponse(buffer, as_attachment=True, filename="feeds_stock_report.pdf")

    if request.method == 'POST':
        return response
    
def feedExpensesReport(request):
    if request.method == 'POST':
        # Get the selected month and year from the form
        selected_month = int(request.POST.get('month'))
        selected_year = int(request.POST.get('year'))

        # Filter FeedsInventory based on the selected month and year
        feeds_expenses = FeedsInventory.objects.filter(date__year=selected_year, date__month=selected_month)

        # Create a buffer for the PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)

        elements = []

        # Create a custom title style
        title_style = ParagraphStyle(
            name='CustomTitleStyle',
            fontSize=14,
            textColor='black',  # Change the title text color
            alignment=1,  # Center alignment
        )
        styles = getSampleStyleSheet()["Heading3"]
        heading = getSampleStyleSheet()["Heading2"]

        total_expenses = Decimal(0)

        # Create a title for the report using the custom style
        elements.append(Paragraph("GOODWILL AGRO INDUSTRIAL DEVELOPMENT CORPORATION", style=heading))
        elements.append(Paragraph("Feeds Expenses for " + datetime(selected_year, selected_month, 1).strftime('%Y-%B'), style=title_style))
        elements.append(Spacer(1, 12))

        # Define the data for the table
        table_data = [['Ration Type', 'Quantity (sacks)', 'Cost', 'Date']]

        for feedsExp in feeds_expenses:
            table_data.append([feedsExp.feeds_ration, feedsExp.quantity, feedsExp.cost, feedsExp.date])
            total_expenses += feedsExp.cost

        totalExpStr = str(total_expenses)

        # Query to aggregate the sum of 'cost' for each unique 'feeds_ration'
        results = FeedsInventory.objects.values('feeds_ration').filter(date__year=selected_year, date__month=selected_month).annotate(total_cost=Sum('cost'))

        # Add results to the list of paragraph elements
        for result in results:
            feeds_ration = result['feeds_ration']
            total_cost = result['total_cost']
            elements.append(Paragraph(f"{feeds_ration}: {total_cost}", styles))

        elements.append(Paragraph("Total Cost: " + totalExpStr, style=styles))

        # Create a table
        table = Table(table_data, colWidths=130, rowHeights=30)
        table.setStyle(TableStyle([
            ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.white),
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.white),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 12))

        # Build the PDF document
        doc.build(elements)
        buffer.seek(0)

        # Create a response with the PDF file
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="feedsExpenses_report.pdf"'
        response.write(buffer.getvalue())
        return response

    return render(request, 'your_form_template.html')