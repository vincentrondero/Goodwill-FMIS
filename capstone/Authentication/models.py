from django.db import models
from datetime import date 

class User(models.Model):
    firstname = models.CharField(max_length=100, default="Juan")
    lastname = models.CharField(max_length=100, default="De la Cruz")
    username = models.CharField(max_length=255)
    password = models.CharField(max_length=255)

    ROLE_CHOICES = [
        ('administrator', 'Administrator'),
        ('user', 'User'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')

    date = models.DateField(default=date.today)

    archive_user = models.BooleanField(default=False) 


class Task(models.Model):
    task_name = models.CharField(max_length=255)
    due_date = models.DateField()
    due_time = models.TimeField()
    description = models.TextField()
    is_done = models.BooleanField(default=False)

class Pig(models.Model):
    pig_id = models.CharField(max_length=255)
    dam = models.CharField(max_length=255)
    dob = models.DateField()
    sire = models.CharField(max_length=255)
    pig_class = models.CharField(max_length=255)
    
    SEX_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
    ]
    sex = models.CharField(max_length=10, choices=SEX_CHOICES)
    
    count = models.PositiveIntegerField()
    weight = models.DecimalField(max_digits=5, decimal_places=2)
    remarks = models.TextField()
    
    verif_by = models.CharField(max_length=255)
    date = models.DateField(default=date.today) 
    barcode_image = models.BinaryField(null=True, blank=True) 

class Sow(models.Model):
    pig_id = models.CharField(max_length=255, null=True)
    dam = models.CharField(max_length=20)
    dob = models.DateField()
    sire = models.CharField(max_length=20)
    pig_class = models.CharField(max_length=20)
    sex = models.CharField(max_length=10)
    count = models.IntegerField()
    weight = models.FloatField()
    remarks = models.TextField()
    verif_by = models.CharField(max_length=50)
    date = models.DateField()


class FeedsInventory(models.Model):
    feeds_brand = models.CharField(max_length=255)
    feeds_ration = models.CharField(max_length=255)
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    verified_by = models.CharField(max_length=255)
    date = models.DateField()

class PigSale(models.Model):
    pig = models.ForeignKey('Pig', on_delete=models.CASCADE)
    weight = models.DecimalField(max_digits=5, decimal_places=2)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    verif_by = models.CharField(max_length=255)
    date = models.DateField()

class MortalityForm(models.Model):
    pig = models.ForeignKey(Pig, on_delete=models.CASCADE, related_name='mortality_forms')
    date = models.DateField()
    pig_class = models.CharField(max_length=255)
    cause = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    remarks = models.CharField(max_length=255)
    reported_by = models.CharField(max_length=255)
    verified_by = models.CharField(max_length=255)

    def is_pig_sold(self):
        return PigSale.objects.filter(pig=self.pig).exists()
    
class Vaccine(models.Model):
    pig = models.ForeignKey(Pig, on_delete=models.CASCADE, related_name='vaccines')
    date = models.DateField()
    vaccine = models.CharField(max_length=255)
    purpose = models.CharField(max_length=255)
    dosage = models.CharField(max_length=255)

    def __str__(self):
        return f"Vaccine for Pig {self.pig.pig_id} - {self.vaccine}"

class Weanling(models.Model):
    pig = models.ForeignKey('Pig', on_delete=models.CASCADE, related_name='weanlings_pig')
    sow = models.ForeignKey('Sow', on_delete=models.CASCADE, related_name='weanlings_sow')
    date = models.DateField()
    weight = models.DecimalField(max_digits=5, decimal_places=2)
    SEX_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
    ]
    sex = models.CharField(max_length=10, choices=SEX_CHOICES)
    remarks = models.TextField()

    def __str__(self):
        return f"Weanling {self.id}"
    
class SowPerformance(models.Model):
    sow_no = models.ForeignKey('Sow', on_delete=models.CASCADE, related_name='sow_perf')
    dam = models.CharField(max_length=20)
    dob = models.CharField(max_length=20)
    sire = models.CharField(max_length=20)
    pig_class = models.CharField(max_length=20)
    pig_parity = models.CharField(max_length=20)

    first_boar = models.CharField(max_length=20)
    second_boar = models.CharField(max_length=20)
    third_boar = models.CharField(max_length=20)
    date_bred = models.DateField()
    date_due = models.DateField()
    date_farr = models.DateField()

    alive = models.IntegerField()
    mk = models.IntegerField()
    sb = models.IntegerField()
    mffd = models.IntegerField()
    total_litter_size = models.IntegerField()
    ave_litter_size = models.IntegerField()

    date_weaned = models.DateField()
    no_weaned = models.IntegerField()
    total_weaned = models.IntegerField()
    ave_weaned = models.FloatField()
    total_kilo_weaned = models.FloatField()

    def __str__(self):
        return f"SowPerformance {self.id}"
    
class FeedStockUpdate(models.Model):
    count_update = models.PositiveIntegerField()
    date = models.DateField()
    verify_by = models.CharField(max_length=255)
    ration = models.CharField(max_length=255, default='Starter')