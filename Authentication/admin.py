from django.contrib import admin
from .models import User, Task, Pig, Sow,FeedsInventory, PigSale, MortalityForm, Vaccine,  Weanling, SowPerformance, FeedStockUpdate

admin.site.register(Task)
admin.site.register(User)
admin.site.register(Pig)
admin.site.register(Sow)
admin.site.register(FeedsInventory)
admin.site.register(PigSale)
admin.site.register(MortalityForm)
admin.site.register(Vaccine)
admin.site.register( Weanling)
admin.site.register(SowPerformance)
admin.site.register(FeedStockUpdate)