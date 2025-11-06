from django.contrib import admin
from .models import *

# @admin.register(Retiree)
# class RetireeAdmin(admin.ModelAdmin):
#     list_display = ('fname', 'email', 'phone', 'field', 'mentorship', 'other_area')

# @admin.register(Seeker)
# class SeekerAdmin(admin.ModelAdmin):
#     list_display = ("name", "email", "interests", "goals")
#     search_fields = ("name", "email", "interests", "goals")
admin.site.register(Retiree)
admin.site.register(Seeker)
admin.site.register(FollowRequest)
admin.site.register(Category)
admin.site.register(Tag)
admin.site.register(BlogPost)
admin.site.register(MentorshipRequest)
admin.site.register(AdminUser)
admin.site.register(BlogComment)
admin.site.register(SavedBlog)
admin.site.register(RetireeBlogComment)
admin.site.register(RetireeSavedBlog)
admin.site.register(Message)
admin.site.register(Report)
