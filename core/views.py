from django.shortcuts import render,redirect,get_object_or_404,Http404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password
from django.contrib.auth.hashers import check_password
from django.core.paginator import Paginator
from .models import Retiree, FollowRequest
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.http import HttpResponse
from django.db.models import Q,Count
from django.utils import timezone
from datetime import datetime
from .models import*
import json 
import re

def home(request):
    return render(request, 'index.html')

def about(request):
    return render(request, 'about.html')

def contact(request):
    return render(request, 'contact.html')
def Faq(request):
    return render(request, 'Faq.html')
def public_blog_list(request, category_slug=None, tag_slug=None):
    blogs = BlogPost.objects.filter(published=True).select_related('author', 'category').prefetch_related('tags')
    
   
    category = None
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        blogs = blogs.filter(category=category)
    
    tag = None
    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        blogs = blogs.filter(tags=tag)

    search_query = request.GET.get('q', '')
    if search_query:
        blogs = blogs.filter(
            Q(title__icontains=search_query) |
            Q(content__icontains=search_query) |
            Q(excerpt__icontains=search_query) |
            Q(author__fname__icontains=search_query) |
            Q(category__name__icontains=search_query) |
            Q(tags__name__icontains=search_query)
        ).distinct()
    
    blogs = blogs.order_by('-created_at')
    categories = Category.objects.annotate(
        blog_count=Count('blogpost', filter=Q(blogpost__published=True))
    ).filter(blog_count__gt=0)
    popular_tags = Tag.objects.annotate(
        blog_count=Count('blogpost', filter=Q(blogpost__published=True))
    ).filter(blog_count__gt=0).order_by('-blog_count')[:10]
    recent_posts = BlogPost.objects.filter(published=True).order_by('-created_at')[:5]
    
    context = {
        'blogs': blogs,
        'categories': categories,
        'popular_tags': popular_tags,
        'recent_posts': recent_posts,
        'current_category': category,
        'current_tag': tag,
        'search_query': search_query,
    }
    
    return render(request, 'public_blog_list.html', context)

def public_blog_detail(request, slug):
    blog = get_object_or_404(
        BlogPost.objects.select_related('author', 'category').prefetch_related('tags'), 
        slug=slug, 
        published=True
    )
    blog.views_count += 1
    blog.save()
    related_blogs = BlogPost.objects.filter(
        published=True
    ).filter(
        Q(category=blog.category) | Q(tags__in=blog.tags.all())
    ).exclude(
        id=blog.id
    ).distinct().order_by('-created_at')[:4]
    recent_posts = BlogPost.objects.filter(published=True).exclude(id=blog.id).order_by('-created_at')[:5]
    
    context = {
        'blog': blog,
        'related_blogs': related_blogs,
        'recent_posts': recent_posts,
    }
    
    return render(request, 'public_blog_detail.html', context)

def public_blog_search(request):
    return public_blog_list(request)

def RRegistration(request):
    if request.method == "POST":
        fname = request.POST.get("name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        password = request.POST.get("password")   
        confirm_password = request.POST.get("confirm_password")
        field = request.POST.get("field")
        experience = request.POST.get("experience")
        bio = request.POST.get("bio")
        proof = request.FILES.get("retirement_proof")
        photo = request.FILES.get("photo")
        mentorship_list = request.POST.getlist("mentorship") 
        mentorship = ", ".join(mentorship_list)  
        other_area = request.POST.get("other_mentorship", "").strip()
        skills = request.POST.get("skills")
        avilabilty = request.POST.get("avilabilty")
        if phone and phone.strip():
            phone = phone.strip()
            cleaned_phone = re.sub(r'[\s\-\(\)]', '', phone)
            phone_pattern = r'^[\+]?[0-9]{10}$'
            
            if not re.match(phone_pattern, cleaned_phone):
                messages.error(request, "Please enter a valid phone number (10-15 digits, may start with +).")
                return render(request, "RRegistration.html", {
                    'request': request
                })
            
            if Retiree.objects.filter(phone=phone).exists():
                messages.error(request, "This phone number is already registered.")
                return render(request, "RRegistration.html", {
                    'request': request
                })
        else:
            phone = "" 

        if password != confirm_password:
            messages.error(request, "Passwords do not match. Please make sure both passwords are the same.")
            return render(request, "RRegistration.html", {
                'request': request
            })

        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
            return render(request, "RRegistration.html", {
                'request': request
            })
        
        if Retiree.objects.filter(email=email).exists():
            messages.error(request, "Email already registered. Please use a different email or login.")
            return render(request, "RRegistration.html", {
                'request': request
            })

        try:
            Retiree.objects.create(
                fname=fname,
                email=email,
                phone=phone,
                password=password,   
                field=field,
                experience=experience,
                bio=bio,
                proof=proof,
                photo=photo,
                mentorship=mentorship,
                other_area=other_area,
                skills=skills,
                avilabilty=avilabilty,
                is_approved=False, 
            )

            messages.success(request, "Registration successful! Your account is pending admin approval. You will be able to login once approved.")
            return redirect("Rlogin")

        except Exception as e:
            messages.error(request, f"An error occurred during registration: {str(e)}")
            return render(request, "RRegistration.html", {
                'request': request
            })

    return render(request, "RRegistration.html")

@csrf_protect
def Rlogin(request):
    if request.method == "POST":
        email = request.POST.get('email')
        password = request.POST.get('password')
        role = request.POST.get('role')  

        if role == "retiree":
            try:
                retiree = Retiree.objects.get(email=email)
                
                if not retiree.is_approved:
                    messages.error(request, "Your account is pending approval from admin. Please wait for approval or contact support.")
                    return redirect("Rlogin")
                
                if retiree.password == password:   
                    request.session['retireeid'] = retiree.id
                    return redirect("Rdashboard")
                else:
                    messages.error(request, "Invalid password for Retiree.")
            except Retiree.DoesNotExist:
                messages.error(request, "No Retiree found with this email.")

        elif role == "seeker":
            try:
                seeker = Seeker.objects.get(email=email)
                if seeker.password == password:  
                    request.session['seekerid'] = seeker.id
                    return redirect("Sdashboard")
                else:
                    messages.error(request, "Invalid password for Seeker.")
            except Seeker.DoesNotExist:
                messages.error(request, "No Seeker found with this email.")
        else:
            messages.error(request, "Please select a valid role.")

        return redirect("Rlogin")  

    return render(request, "Rlogin.html")


def Rlogout(request):
    request.session.delete("retireeid")   
    return redirect("home")

def Slogout(request):
    request.session.delete("seekerid")   
    return redirect("home")

def Rdashboard(request):
    if 'retireeid' not in request.session:
        return redirect("Rlogin")  

    retiree = Retiree.objects.get(id=request.session['retireeid'])

    follow_requests_count = FollowRequest.objects.filter(
        retiree=retiree, status="pending"
    ).count()

    conversations_count = Seeker.objects.filter(
        models.Q(sent_messages__receiver_retiree=retiree) |
        models.Q(received_messages__sender_retiree=retiree)
    ).distinct().count()

    total_requests = MentorshipRequest.objects.filter(mentor=retiree).count()
    total_blogs = BlogPost.objects.filter(author=retiree).count()
    total_pending = MentorshipRequest.objects.filter(mentor=retiree, status="Pending").count()

    total_feedback = 0

    return render(request, "Rdashboard.html", {
        'retiree': retiree,
        'follow_requests_count': follow_requests_count,
        'conversations_count': conversations_count,
        'total_requests': total_requests,
        'total_blogs': total_blogs,
        'total_pending': total_pending,
        'total_feedback': total_feedback,
    })


def follow_requests(request):
    if 'retireeid' not in request.session:
        return redirect("Rlogin")

    retiree = get_object_or_404(Retiree, id=request.session['retireeid'])
    requests = FollowRequest.objects.filter(retiree=retiree, status="pending")

    return render(request, "follow_requests.html", {
        "retiree": retiree,
        "requests": requests
    })

def accept_request(request, req_id):
    follow_request = get_object_or_404(FollowRequest, id=req_id)
    follow_request.status = "accepted"
    follow_request.save()
    return redirect("follow_requests")


def reject_request(request, req_id):
    follow_request = get_object_or_404(FollowRequest, id=req_id)
    follow_request.status = "rejected"
    follow_request.save()
    return redirect("follow_requests")

def retiree_login_required(view_func):
    def wrapper(request, *args, **kwargs):
        if 'retireeid' not in request.session:
            return redirect("Rlogin")
        return view_func(request, *args, **kwargs)
    return wrapper


@retiree_login_required
def mentor_dashboardprofile(request):
    if 'retireeid' not in request.session:
        messages.error(request, "Please log in to access your dashboard.")
        return redirect("Rlogin")

    mentor = get_object_or_404(Retiree, id=request.session['retireeid'])

    blogs = BlogPost.objects.filter(author=mentor).order_by('-created_at')

    followers_count = FollowRequest.objects.filter(retiree=mentor, status="accepted").count()

    following_count = 0  
    blogs_count = blogs.count()

    saved_blogs = RetireeSavedBlog.objects.filter(retiree=mentor).select_related('blog', 'blog__author').order_by('-saved_at')
    saved_blogs_count = saved_blogs.count()

    return render(request, "mentor_dashboardprofile.html", {
        "mentor": mentor,
        "blogs": blogs,
        "saved_blogs": saved_blogs,
        "followers_count": followers_count,
        "following_count": following_count,
        "blogs_count": blogs_count,
        "saved_blogs_count": saved_blogs_count,
    })

def view_blog(request, slug):
    blog = get_object_or_404(BlogPost, slug=slug, published=True)
    blog.views_count += 1
    blog.save()
    
    seeker_id = request.session.get('seekerid')
    liked_by_user = saved_by_user = False
    if seeker_id:
        seeker = Seeker.objects.get(id=seeker_id)
        liked_by_user = seeker in blog.likes.all()
        saved_by_user = seeker in blog.saves.all()

    return render(request, "view_blog.html", {
        "blog": blog,
        "liked_by_user": liked_by_user,
        "saved_by_user": saved_by_user
    })


@login_required
def edit_mentor_profile(request):
    if 'retireeid' not in request.session:
        return redirect("Rlogin")

    mentor = get_object_or_404(Retiree, id=request.session['retireeid'])

    if request.method == "POST":
        bio = request.POST.get("bio")
        if bio:
            mentor.bio = bio
            mentor.save()
            messages.success(request, "Your bio was updated successfully!")
        return redirect("mentor_dashboardprofile")

    return redirect("mentor_dashboardprofile")


@login_required
def change_profile_photo(request):
    if 'retireeid' not in request.session:
        return redirect("Rlogin")

    mentor = get_object_or_404(Retiree, id=request.session['retireeid'])

    if request.method == "POST" and request.FILES.get("photo"):
        mentor.photo = request.FILES["photo"]
        mentor.save()
        messages.success(request, "Profile picture updated successfully!")
        return redirect("mentor_dashboardprofile")

    return redirect("mentor_dashboardprofile")


def add_blog(request, mentor_id):
    categories = Category.objects.all()
    tags = Tag.objects.all()

    if request.method == "POST":
        title = request.POST.get("title")
        excerpt = request.POST.get("excerpt")
        content = request.POST.get("content")
        category_id = request.POST.get("category")
        tag_ids = request.POST.getlist("tags")
        image = request.FILES.get("image")
        publish = "publish" in request.POST
        mentor = get_object_or_404(Retiree, id=request.session['retireeid'])

        blog = BlogPost(
            author=mentor,
            title=title,
            excerpt=excerpt,
            content=content,
            published=publish,
            image=image,
            category=Category.objects.get(id=category_id) if category_id else None
        )
        blog.save()

        if tag_ids:
            blog.tags.set(Tag.objects.filter(id__in=tag_ids))

        messages.success(request, "Blog saved successfully!")
        return redirect('mentor_dashboardprofile')

    return render(request, "add_blog.html", {
        "categories": categories,
        "tags": tags,
        "mentor_id": mentor_id,
    })

def mentorship_requests(request):
    if 'retireeid' not in request.session:
        return redirect("Rlogin")  

    retiree = Retiree.objects.get(id=request.session['retireeid'])
    requests = MentorshipRequest.objects.filter(mentor=retiree).order_by('-request_date')

    total_requests = requests.count()
    total_pending = requests.filter(status="Pending").count()
    total_accepted = requests.filter(status="Accepted").count()
    total_declined = requests.filter(status="Declined").count()

    return render(request, "mentorship_requests.html", {
        'retiree': retiree,
        'requests': requests,
        'total_requests': total_requests,
        'total_pending': total_pending,
        'total_accepted': total_accepted,
        'total_declined': total_declined,
    })

def respond_mentorship_request(request, req_id, action):
    req = get_object_or_404(MentorshipRequest, id=req_id)
    if action == "accept":
        req.status = "Accepted"
        messages.success(request, f"Mentorship request from {req.learner.name} accepted.")
    elif action == "decline":
        req.status = "Declined"
        messages.warning(request, f"Mentorship request from {req.learner.name} declined.")
    req.save()
    return redirect("mentorship_requests")
# <-------------------------seeker-------------->
def SRegistration(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        password = request.POST.get("password")   
        interests = request.POST.get("interests")
        goals = request.POST.get("goals")
        photo = request.FILES.get("photo")  

        if not email:
            messages.error(request, "Email is required.")
            return render(request, "SRegistration.html", {
                'request': request
            })

        if '@' not in email or '.' not in email:
            messages.error(request, "Please enter a valid email address.")
            return render(request, "SRegistration.html", {
                'request': request
            })

        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            messages.error(request, "Please enter a valid email address (e.g., example@domain.com).")
            return render(request, "SRegistration.html", {
                'request': request
            })

        if Seeker.objects.filter(email=email).exists():
            messages.error(request, "Email already registered. Please use a different email or login.")
            return render(request, "SRegistration.html", {
                'request': request
            })

        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
            return render(request, "SRegistration.html", {
                'request': request
            })

        try:
            Seeker.objects.create(
                name=name,
                email=email,
                password=password,  
                interests=interests,
                goals=goals,
                photo=photo  
            )

            messages.success(request, "Registration successful! Please login.")
            return redirect("Rlogin")

        except Exception as e:
            messages.error(request, f"An error occurred during registration: {str(e)}")
            return render(request, "SRegistration.html", {
                'request': request
            })

    return render(request, "SRegistration.html")

def Sdashboard(request):
    if 'seekerid' not in request.session:
        return redirect("Rlogin")
    
    try:
        seeker = Seeker.objects.get(id=request.session['seekerid'])
        print(f"Seeker: {seeker.name}")
        print(f"Photo: {seeker.photo}")
        if seeker.photo:
            print(f"Photo URL: {seeker.photo.url}")
        
        return render(request, "Sdashboard.html", {'seeker': seeker})
    
    except Seeker.DoesNotExist:
        messages.error(request, "Seeker not found.")
        return redirect("Rlogin")
    except Exception as e:
        messages.error(request, f"Error loading dashboard: {str(e)}")
        return redirect("Rlogin")

def mentors_browsing(request):
    q = request.GET.get('q', '')
    field = request.GET.get('field', '')
    exp = request.GET.get('exp', '')

    mentors = Retiree.objects.all()
    if q:
        mentors = mentors.filter(fname__icontains=q)
    if field:
        mentors = mentors.filter(field__icontains=field)
    if exp:
        mentors = mentors.filter(experience__icontains=exp)

    paginator = Paginator(mentors, 4)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    if 'seekerid' in request.session:
        seeker = Seeker.objects.get(id=request.session['seekerid'])
        for mentor in page_obj:
            req = FollowRequest.objects.filter(seeker=seeker, retiree=mentor).first()
            mentor.follow_status = req.status if req else None
    else:
        for mentor in page_obj:
            mentor.follow_status = None

    return render(request, "mentors_browsing.html", {
        "page_obj": page_obj
    })

def vieweachretireeprofile(request, mentor_id):
    mentor = get_object_or_404(Retiree, id=mentor_id)

    follow_status = None

    if 'seekerid' in request.session:
        seeker = Seeker.objects.get(id=request.session['seekerid'])
        follow = FollowRequest.objects.filter(seeker=seeker, retiree=mentor).first()
        if follow:
            follow_status = follow.status

    mentor.follow_status = follow_status

    followers_count = FollowRequest.objects.filter(retiree=mentor, status="accepted").count()

    mentees_count = MentorshipRequest.objects.filter(mentor=mentor, status="Accepted").count()
    
    blogs_count = BlogPost.objects.filter(author=mentor, published=True).count()
    blogs = BlogPost.objects.filter(author=mentor, published=True)
    skills = mentor.skills.split(",") if mentor.skills else []
        
    availability = []
    if mentor.avilabilty:
       availability.append({"time": mentor.avilabilty})
       
    context = {
        'mentor': mentor,
        'followers_count': followers_count, 
        'mentees_count': mentees_count,      
        'blogs_count': blogs_count,
        'skills': skills,
        'availability': availability,
        'blogs': blogs,
    }
    return render(request, 'vieweachretireeprofile.html', context)


def view_mentor_blog(request, blog_id):
    blog = get_object_or_404(BlogPost, id=blog_id, published=True)
    mentor = blog.author  # Assuming 'author' is FK to Mentor

    context = {
        'blog': blog,
        'mentor': mentor,
    }
    return render(request, 'mentor_blog_detail.html', context)

def mentor_profile(request, id):
    mentor = Retiree.objects.get(id=id)
    return render(request, "mentor_profile.html", {"mentor": mentor})



def follow_mentor(request, mentor_id):
    if 'seekerid' not in request.session:
        messages.error(request, "You must log in as a seeker to follow.")
        return redirect("Slogin")

    seeker = get_object_or_404(Seeker, id=request.session['seekerid'])
    retiree = get_object_or_404(Retiree, id=mentor_id)

    follow_request, created = FollowRequest.objects.get_or_create(
        seeker=seeker, retiree=retiree,
        defaults={"status": "pending"}
    )

    if not created:
        if follow_request.status == "pending":
            messages.info(request, "Follow request already sent.")
        elif follow_request.status == "accepted":
            messages.info(request, "You are already following this mentor.")
    else:
        messages.success(request, f"Follow request sent to {retiree.fname}!")

    return redirect("mentors_browsing")

def send_mentorship_request(request, mentorid):
    if 'seekerid' not in request.session:
        messages.error(request, "You must log in as a seeker to send mentorship requests.")
        return redirect("Slogin")

    seeker = get_object_or_404(Seeker, id=request.session['seekerid'])
    mentor = get_object_or_404(Retiree, id=mentorid)

    if request.method == "POST":
        topic = request.POST.get("topic")
        message = request.POST.get("message")


        if MentorshipRequest.objects.filter(
            learner=seeker, mentor=mentor, topic__iexact=topic, status="Pending"
        ).exists():
            messages.info(request, "You already sent a mentorship request on this topic.")
            return redirect("mentors_browsing")

        MentorshipRequest.objects.create(
            learner=seeker,
            mentor=mentor,
            topic=topic,
            message=message,
        )
        messages.success(request, f"Mentorship request sent to {mentor.fname}!")
        return redirect("mentors_browsing")

    return render(request, "send_mentorship_request.html", {"mentor": mentor})


def seeker_mentorship_requests(request):
    if 'seekerid' not in request.session:
        messages.error(request, "Please log in to view your mentorship requests.")

        return redirect("Slogin")

    try:
        seeker = get_object_or_404(Seeker, id=request.session['seekerid'])
        requests = MentorshipRequest.objects.filter(learner=seeker).order_by('-request_date')
        pendingrequests = requests.filter(status = "Pending").count()
        accepted = requests.filter(status = "Accepted").count()
        totalrequests = requests.count()
        rejected = requests.filter(status = "Declined").count()
        return render(request, "seeker_mentorship_requests.html", {
            "requests": requests,
            "pendingrequests":pendingrequests,
            "accepted":accepted,
            "totalrequests":totalrequests,
            "rejected":rejected
        })
    except Exception as e:
        print("Error:", e)
        messages.error(request, "Something went wrong while fetching your requests.")
        return redirect("Sdashboard")
    
def unsend_mentorship_request(request, request_id):
    if 'seekerid' not in request.session:
        messages.error(request, "Please log in to manage requests.")
        return redirect("Slogin")

    seeker = Seeker.objects.get(id=request.session['seekerid'])
    mentorship_request = get_object_or_404(MentorshipRequest, id=request_id, learner=seeker)

    if request.method == "POST":
        mentorship_request.delete()
        messages.success(request, "Your mentorship request has been unsent successfully.")
        return redirect("seeker_mentorship_requests")

    messages.error(request, "Invalid request.")
    return redirect("seeker_mentorship_requests")


def seeker_dashboardprofile(request):
    if 'seekerid' not in request.session:
        messages.error(request, "Please log in first.")
        return redirect("Slogin")
    try:
       seeker = get_object_or_404(Seeker, id=request.session['seekerid'])
       total_requests = MentorshipRequest.objects.filter(learner=seeker).count()
       accepted_requests = MentorshipRequest.objects.filter(learner=seeker, status="Accepted").count()
       pending_requests = MentorshipRequest.objects.filter(learner=seeker, status="Pending").count()
   
       followbacks = FollowRequest.objects.filter(seeker=seeker, status="accepted").count()
   
       current_mentors = MentorshipRequest.objects.filter(
       status="Accepted",learner=seeker)
       
       saved_blogs_count = SavedBlog.objects.filter(seeker=seeker).count()
       saved_blogs = SavedBlog.objects.filter(seeker=seeker).select_related('blog', 'blog__author').order_by('-saved_at')[:5]  

       return render(request, "seeker_dashboardprofile.html", {
           "seeker": seeker,
           "total_requests": total_requests,
           "accepted_requests": accepted_requests,
           "pending_requests": pending_requests,
           "followbacks": followbacks,
           "current_mentors": current_mentors,
           "saved_blogs_count": saved_blogs_count,  
           "saved_blogs": saved_blogs,  
       })
    except Exception as e:
        print("Error:", e)
        messages.error(request, "Something went wrong while fetching your requests.")
        return redirect("Sdashboard")


def edit_seeker_goals(request):
    try:
        if 'seekerid' not in request.session:
            messages.error(request, "Please log in first.")
            return redirect("Slogin")

        seeker = get_object_or_404(Seeker, id=request.session['seekerid'])

        if request.method == "POST":
            seeker.goals = request.POST.get("goals", seeker.goals)
            seeker.save()
            messages.success(request, "Goals updated successfully!")

    except Seeker.DoesNotExist:
        messages.error(request, "Seeker not found.")
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")

    return redirect("seeker_dashboardprofile")

def edit_seeker_interests(request):
    try:
        if 'seekerid' not in request.session:
            messages.error(request, "Please log in first.")
            return redirect("Slogin")

        seeker = get_object_or_404(Seeker, id=request.session['seekerid'])

        if request.method == "POST":
            seeker.interests = request.POST.get("interests", seeker.interests)
            seeker.save()
            messages.success(request, "Interests updated successfully!")

    except Seeker.DoesNotExist:
        messages.error(request, "Seeker not found.")
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")

    return redirect("seeker_dashboardprofile")



def change_seeker_photo(request):
    try:
        if 'seekerid' not in request.session:
            messages.error(request, "Please log in first.")
            return redirect("Slogin")
        
        seeker = get_object_or_404(Seeker, id=request.session['seekerid'])

        if request.method == "POST" and request.FILES.get("photo"):
            seeker.photo = request.FILES["photo"]
            seeker.save()
            messages.success(request, "Profile picture updated successfully!")
            
    except Seeker.DoesNotExist:
        messages.error(request, "Seeker not found.")
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
    
    return redirect("seeker_dashboardprofile")


def seeker_blog_feed(request):
    try:
      
        seeker_id = request.session.get('seekerid')
        blogs = BlogPost.objects.filter(published=True).select_related('author').prefetch_related('tags','comments').order_by('-created_at')
        comments = BlogComment.objects.filter(post__in = blogs)
        
        savedblog = []
        if 'seekerid' in request.session:
            seeker = Seeker.objects.get(id=request.session['seekerid'])
            savedblog = seeker.saved_blog_posts.all().values_list('blog_id', flat=True)
        
        paginator = Paginator(blogs, 5)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
 
        context = {
            "page_obj": page_obj,  
            "seeker": seeker if 'seekerid' in request.session else None,
            "comments": comments,
            "savedblog": savedblog,
        }
        
        return render(request, "seeker_blog_feed.html", context)
        
    except (Seeker.DoesNotExist, KeyError):

        seeker = None
        blogs = BlogPost.objects.filter(published=True).order_by('-created_at')
        paginator = Paginator(blogs, 5)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        return render(request, "seeker_blog_feed.html", {
            "page_obj": page_obj,
            "seeker": None,
            "comments": BlogComment.objects.none(),
            "savedblog": [],
        })
def like_blog(request, blog_id):
    if 'seekerid' not in request.session:
        messages.error(request, "Please log in to like a blog.")
        return redirect("Slogin")

    seeker = Seeker.objects.get(id=request.session['seekerid'])
    blog = get_object_or_404(BlogPost, id=blog_id)
    
    if seeker in blog.likes.all():
        blog.likes.remove(seeker)
    else:
        blog.likes.add(seeker)
    return redirect(request.META.get('HTTP_REFERER', 'seeker_blog_feed'))


def save_blog(request, blog_id):
    if 'seekerid' not in request.session:
        messages.error(request, "Please log in to save a blog.")
        return redirect("Slogin")

    seeker = Seeker.objects.get(id=request.session['seekerid'])
    blog = get_object_or_404(BlogPost, id=blog_id)

    saved_blog, created = SavedBlog.objects.get_or_create(seeker=seeker, blog=blog)

    if not created:
        saved_blog.delete()
    return redirect(request.META.get('HTTP_REFERER', 'seeker_blog_feed'))


def add_comment(request, blog_id):
    if 'seekerid' not in request.session:
        messages.error(request, "Please log in to comment.")
        return redirect("Slogin")
    
    blog = get_object_or_404(BlogPost, id=blog_id)
    seeker = get_object_or_404(Seeker, id=request.session['seekerid'])
    
    if request.method == "POST":
        comment_text = request.POST.get("comment")
        if comment_text:
            BlogComment.objects.create(post=blog, user=seeker, comment=comment_text)
            messages.success(request, "Comment added successfully!")
    return redirect("seeker_blog_feed")

def Slogin(request):
    return render(request,"Slogin.html")

def chat(request, mentor_id):
    if 'seekerid' not in request.session:
        return redirect("Slogin")
    
    seeker = get_object_or_404(Seeker, id=request.session['seekerid'])
    mentor = get_object_or_404(Retiree, id=mentor_id)

    if request.method == 'POST':
        message_content = request.POST.get('message')
        if message_content and message_content.strip():

            Message.objects.create(
                sender_seeker=seeker,
                receiver_retiree=mentor,
                content=message_content.strip()
            )
            messages.success(request, "Message sent!")
            return redirect('chat', mentor_id=mentor_id)
    

    messages_list = Message.objects.filter(
        models.Q(sender_seeker=seeker, receiver_retiree=mentor) |
        models.Q(sender_retiree=mentor, receiver_seeker=seeker)
    ).order_by('timestamp')
    
    return render(request, 'chat.html', {
        'seeker': seeker,
        'mentor': mentor,
        'messages': messages_list,
        'mentor_id': mentor_id,
        'current_time': timezone.now() 
    })



def retiree_chat(request, seeker_id):
    if 'retireeid' not in request.session:
        return redirect("Rlogin")
    
    retiree = get_object_or_404(Retiree, id=request.session['retireeid'])
    seeker = get_object_or_404(Seeker, id=seeker_id)
    
    if request.method == 'POST':
        message_content = request.POST.get('message')
        if message_content and message_content.strip():
            Message.objects.create(
                sender_retiree=retiree,
                receiver_seeker=seeker,
                content=message_content.strip()
            )
            messages.success(request, "Message sent!")
            return redirect('retiree_chat', seeker_id=seeker_id)

    messages_list = Message.objects.filter(
        models.Q(sender_seeker=seeker, receiver_retiree=retiree) |
        models.Q(sender_retiree=retiree, receiver_seeker=seeker)
    ).order_by('timestamp')

    conversations = []
    all_seekers = Seeker.objects.filter(
        models.Q(sent_messages__receiver_retiree=retiree) |
        models.Q(received_messages__sender_retiree=retiree)
    ).distinct()
    
    for conv_seeker in all_seekers:
        last_message = Message.objects.filter(
            models.Q(sender_seeker=conv_seeker, receiver_retiree=retiree) |
            models.Q(sender_retiree=retiree, receiver_seeker=conv_seeker)
        ).order_by('-timestamp').first()
        
        conversations.append({
            'seeker': conv_seeker,
            'last_message': last_message.content if last_message else 'No messages yet',
            'last_message_time': last_message.timestamp if last_message else None,
        })
    
    return render(request, 'retiree_chat.html', {
        'retiree': retiree,
        'seeker': seeker,
        'messages': messages_list,
        'conversations': conversations,
        'seeker_id': seeker_id,
        'current_time': timezone.now()
    })


def retiree_chat_inbox(request):
    if 'retireeid' not in request.session:
        return redirect("Rlogin")
    
    retiree = get_object_or_404(Retiree, id=request.session['retireeid'])
    
    conversations = []
    all_seekers = Seeker.objects.filter(
        models.Q(sent_messages__receiver_retiree=retiree) |
        models.Q(received_messages__sender_retiree=retiree)
    ).distinct()
    
    for seeker in all_seekers:
        last_message = Message.objects.filter(
            models.Q(sender_seeker=seeker, receiver_retiree=retiree) |
            models.Q(sender_retiree=retiree, receiver_seeker=seeker)
        ).order_by('-timestamp').first()
        
        unread_count = 0
        
        conversations.append({
            'seeker': seeker,
            'last_message': last_message.content if last_message else 'No messages yet',
            'last_message_time': last_message.timestamp if last_message else None,
            'unread_count': unread_count
        })
    
    conversations.sort(key=lambda x: x['last_message_time'] if x['last_message_time'] else timezone.make_aware(datetime.min), reverse=True)
    
    return render(request, 'retiree_chat_inbox.html', {
        'retiree': retiree,
        'conversations': conversations
    })

def retiree_blog_feed(request):
    try:
        blogs_list = BlogPost.objects.all().select_related('author').prefetch_related('tags').order_by('-created_at')
        
        paginator = Paginator(blogs_list, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
      
        current_retiree = None
        saved_blog_ids = []
        liked_blog_ids = []
        
        if 'retireeid' in request.session:
            retiree_id = request.session['retireeid']
            current_retiree = get_object_or_404(Retiree, id=retiree_id)
            
            saved_blogs = RetireeSavedBlog.objects.filter(retiree=current_retiree).values_list('blog_id', flat=True)
            saved_blog_ids = list(saved_blogs)
            liked_blog_ids = request.session.get('retiree_liked_blogs', [])

        for blog in page_obj:
            blog.likes_count = blog.likes.count() + len(liked_blog_ids)  
            blog.comments_count = blog.comments.count() + blog.Retireecomments.count()
            blog.is_saved = blog.id in saved_blog_ids
            blog.is_liked = blog.id in liked_blog_ids
        
        context = {
            'blogs': page_obj,
            'page_obj': page_obj,
            'current_retiree': current_retiree,
        }
        
        return render(request, 'retiree_blog_feed.html', context)
        
    except Exception as e:
        messages.error(request, f"Error loading blogs: {str(e)}")
        return render(request, 'retiree_blog_feed.html', {'blogs': []})

def retiree_like_blog(request, blog_id):
    if 'retireeid' not in request.session:
        messages.error(request, "Please log in to like blogs.")
        return redirect('Rlogin')
    
    try:
        blog = get_object_or_404(BlogPost, id=blog_id)
        retiree = get_object_or_404(Retiree, id=request.session['retireeid'])
        
        liked_blogs = request.session.get('retiree_liked_blogs', [])
        
        if blog_id in liked_blogs:
            liked_blogs.remove(blog_id)
            liked = False
            message = "Blog unliked successfully."
        else:
            liked_blogs.append(blog_id)
            liked = True
            message = "Blog liked successfully!"

        request.session['retiree_liked_blogs'] = liked_blogs
        request.session.modified = True
      
        seeker_likes_count = blog.likes.count()
        retiree_likes_count = len(liked_blogs)
        total_likes = seeker_likes_count + retiree_likes_count
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'liked': liked,
                'likes_count': total_likes,
                'message': message
            })
        else:
            messages.success(request, message)
            return redirect('retiree_blog_feed')
        
    except Exception as e:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': f"Error liking blog: {str(e)}"
            })
        else:
            messages.error(request, f"Error liking blog: {str(e)}")
            return redirect('retiree_blog_feed')

def retiree_save_blog(request, blog_id):

    if 'retireeid' not in request.session:
        messages.error(request, "Please log in to save blogs.")
        return redirect('Rlogin')
    
    try:
        blog = get_object_or_404(BlogPost, id=blog_id)
        retiree = get_object_or_404(Retiree, id=request.session['retireeid'])
        
        existing_save = RetireeSavedBlog.objects.filter(blog=blog, retiree=retiree).first()
        
        if existing_save:
            existing_save.delete()
            saved = False
            message = "Blog removed from saved list."
        else:

            RetireeSavedBlog.objects.create(blog=blog, retiree=retiree)
            saved = True
            message = "Blog saved successfully!"
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'saved': saved,
                'message': message
            })
        else:
            messages.success(request, message)
            return redirect('retiree_blog_feed')
        
    except Exception as e:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': f"Error saving blog: {str(e)}"
            })
        else:
            messages.error(request, f"Error saving blog: {str(e)}")
            return redirect('retiree_blog_feed')

def retiree_add_comment(request, blog_id):
    if 'retireeid' not in request.session:
        messages.error(request, "Please log in to comment on blogs.")
        return redirect('Rlogin')
    
    if request.method == 'POST':
        try:
            blog = get_object_or_404(BlogPost, id=blog_id)
            retiree = get_object_or_404(Retiree, id=request.session['retireeid'])
            comment_text = request.POST.get('comment', '').strip()
            
            if not comment_text:
                messages.error(request, "Comment cannot be empty.")
                return redirect('retiree_blog_feed')
            RetireeBlogComment.objects.create(
                post=blog,
                retiree=retiree,  
                comment=comment_text
            )
            
            messages.success(request, "Comment added successfully!")
            return redirect('retiree_blog_feed')
            
        except Exception as e:
            messages.error(request, f"Error adding comment: {str(e)}")
            return redirect('retiree_blog_feed')
    
    return redirect('retiree_blog_feed')

def retiree_blog_detail(request, blog_id):

    try:
        blog = get_object_or_404(BlogPost, id=blog_id, published=True)
        
        current_retiree = None
        is_saved = False
        is_liked = False
        
        if 'retireeid' in request.session:
            retiree_id = request.session['retireeid']
            current_retiree = get_object_or_404(Retiree, id=retiree_id)
            
            is_saved = RetireeSavedBlog.objects.filter(blog=blog, retiree=current_retiree).exists()
            
            liked_blogs = request.session.get('retiree_liked_blogs', [])
            is_liked = blog_id in liked_blogs
        
        blog.views_count += 1
        blog.save()
        
        seeker_likes_count = blog.likes.count()
        retiree_likes_count = len(request.session.get('retiree_liked_blogs', []))
        total_likes = seeker_likes_count + retiree_likes_count
        
        comments = RetireeBlogComment.objects.filter(post=blog).select_related('user').order_by('-created_at')
        
        context = {
            'blog': blog,
            'mentor': blog.author,
            'likes_count': total_likes,
            'is_saved': is_saved,
            'is_liked': is_liked,
            'current_retiree': current_retiree,
            'comments': comments,
        }
        
        return render(request, 'retiree_blog_detail.html', context)
        
    except Exception as e:
        messages.error(request, f"Error loading blog: {str(e)}")
        return redirect('retiree_blog_feed')
# <-------------------------------------------------# admin---------------------------------------------------->


def admin_login(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        
        try:
            admin = AdminUser.objects.get(username=username)
            if admin.password == password:
                request.session['adminid'] = admin.id
                request.session['adminname'] = admin.name
                return redirect('admin_dashboard')
            else:
                messages.error(request, "Invalid password")
        except AdminUser.DoesNotExist:
            messages.error(request, "Admin not found")
    return render(request, 'admin_login.html')


def admin_dashboard(request):
    if not request.session.get('adminid'):
        return redirect('admin_login')
    pending_mentors_count = Retiree.objects.filter(is_approved=False).count()

    total_retirees = Retiree.objects.count()
    total_seekers = Seeker.objects.count()
    total_blogs = BlogPost.objects.count()
    pending_follow_requests = FollowRequest.objects.filter(status='Pending').count()
    pending_mentorship_requests = MentorshipRequest.objects.filter(status='Pending').count()

    total_reports = Report.objects.count()
    pending_reports = Report.objects.filter(status='pending').count()
    high_urgency_reports = Report.objects.filter(urgency='high').count()

    recent_follow_requests = FollowRequest.objects.order_by('-id')[:5]
    recent_mentorship_requests = MentorshipRequest.objects.order_by('-id')[:5]
    recent_blogs = BlogPost.objects.order_by('-id')[:5]
    recent_reports = Report.objects.select_related('reporter_retiree', 'reporter_seeker').order_by('-created_at')[:5]
    
    context = {
        'total_retirees': total_retirees,
        'total_seekers': total_seekers,
        'total_blogs': total_blogs,
        'pending_follow_requests': pending_follow_requests,
        'pending_mentorship_requests': pending_mentorship_requests,
        'recent_follow_requests': recent_follow_requests,
        'recent_mentorship_requests': recent_mentorship_requests,
        'recent_blogs': recent_blogs,
        'total_reports': total_reports,
        'pending_reports': pending_reports,
        'high_urgency_reports': high_urgency_reports,
        'recent_reports': recent_reports,
        'pending_mentors_count': pending_mentors_count,
    }
    
    return render(request, 'admin_dashboard.html', context)

def admin_mentor_approval(request):
    """Admin view to approve/reject mentors"""
    if not request.session.get('adminid'):
        return redirect('admin_login')
    
    pending_mentors = Retiree.objects.filter(is_approved=False).order_by('-id')

    approved_mentors = Retiree.objects.filter(is_approved=True).order_by('-id')

    total_pending = pending_mentors.count()
    total_approved = approved_mentors.count()
    total_mentors = Retiree.objects.count()
    
    if request.method == 'POST':
        mentor_id = request.POST.get('mentor_id')
        action = request.POST.get('action')
        
        try:
            mentor = Retiree.objects.get(id=mentor_id)
            
            if action == 'approve':
                mentor.is_approved = True
                mentor.save()
                messages.success(request, f'Mentor {mentor.fname} has been approved successfully!')
            
            elif action == 'reject':
                mentor.delete()
                messages.success(request, f'Mentor {mentor.fname} has been rejected and removed.')
            
            elif action == 'revoke':
                mentor.is_approved = False
                mentor.save()
                messages.warning(request, f'Mentor {mentor.fname} approval has been revoked.')
                
        except Retiree.DoesNotExist:
            messages.error(request, 'Mentor not found.')
        
        return redirect('admin_mentor_approval')
    
    context = {
        'pending_mentors': pending_mentors,
        'approved_mentors': approved_mentors,
        'total_pending': total_pending,
        'total_approved': total_approved,
        'total_mentors': total_mentors,
    }
    
    return render(request, 'admin_mentor_approval.html', context)

def admin_blog_action(request, blog_id, action):
    blog = get_object_or_404(BlogPost, id=blog_id)
    if action == "approve":
        blog.published = True
        blog.save()
    elif action == "reject":
        blog.published = False
        blog.save()
    elif action == "delete":
        blog.delete()
    return redirect("admin_dashboard")

def admin_deleteblog_action(request, blog_id, action):
    blog = get_object_or_404(BlogPost, id=blog_id)
    
    if action == 'delete':
        blog_title = blog.title
        blog.delete()
        messages.success(request, f'Blog "{blog_title}" has been deleted successfully!')
    
    return redirect('admin_blog_management')

def admin_user_management(request):
    """User Management Main View"""
    if not request.session.get('adminid'):
        return redirect('admin_login')

    retirees = Retiree.objects.all().order_by('-id')
    seekers = Seeker.objects.all().order_by('-id')

    total_retirees = retirees.count()
    total_seekers = seekers.count()
    active_users = total_retirees + total_seekers
    suspended_users = 0
    
    context = {
        'retirees': retirees,
        'seekers': seekers,
        'total_retirees': total_retirees,
        'total_seekers': total_seekers,
        'active_users': active_users,
        'suspended_users': suspended_users,
        'year': datetime.now().year,
    }
    
    return render(request, 'admin_user_management.html', context)

def retiree_list(request):
    retirees = Retiree.objects.all().order_by('-id')
    search_query = request.GET.get('search', '')
    
    if search_query:
        retirees = retirees.filter(
            Q(fname__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(field__icontains=search_query) |
            Q(experience__icontains=search_query)
        )
    
    retirees_data = []
    for retiree in retirees:
        retirees_data.append({
            'id': retiree.id,
            'name': retiree.fname,
            'email': retiree.email,
            'phone': retiree.phone,
            'field': retiree.field,
            'experience': retiree.experience,
            'bio': retiree.bio,
            'mentorship': retiree.mentorship,
            'skills': retiree.skill_list(),
            'availability': retiree.avilabilty,
            'date_joined': 'Recently',  
            'avatar_initials': retiree.fname[0].upper() if retiree.fname else 'R'
        })
    
    return JsonResponse({'retirees': retirees_data})

def seeker_list(request):
    seekers = Seeker.objects.all().order_by('-id')

    search_query = request.GET.get('search', '')
    
    if search_query:
        seekers = seekers.filter(
            Q(name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(interests__icontains=search_query) |
            Q(goals__icontains=search_query)
        )
    
    seekers_data = []
    for seeker in seekers:
        seekers_data.append({
            'id': seeker.id,
            'name': seeker.name,
            'email': seeker.email,
            'interests': seeker.interests,
            'goals': seeker.goals,
            'date_joined': 'Recently',  
            'avatar_initials': seeker.name[0].upper() if seeker.name else 'S'
        })
    
    return JsonResponse({'seekers': seekers_data})



def delete_retiree(request, retiree_id):
    retiree = Retiree.objects.get(id=retiree_id)
    retiree.delete()
    return redirect("admin_user_management")

def delete_seeker(request, seeker_id):
    seeker = Seeker.objects.get(id=seeker_id)
    seeker.delete()
    return redirect("admin_user_management")

def admin_blog_management(request):
    blogs = BlogPost.objects.all().select_related('author', 'category').prefetch_related('tags').order_by('-created_at')
    
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    category_filter = request.GET.get('category', '')

    if search_query:
        blogs = blogs.filter(
            Q(title__icontains=search_query) |
            Q(content__icontains=search_query) |
            Q(author__fname__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )
    
    if status_filter:
        if status_filter == 'published':
            blogs = blogs.filter(published=True)
        elif status_filter == 'draft':
            blogs = blogs.filter(published=False)
    
    if category_filter:
        blogs = blogs.filter(category_id=category_filter)

    categories = Category.objects.all()
    
    context = {
        'blogs': blogs,
        'categories': categories,
        'total_blogs': blogs.count(),
        'published_blogs': BlogPost.objects.filter(published=True).count(),
        'draft_blogs': BlogPost.objects.filter(published=False).count(),
        'search_query': search_query,
        'status_filter': status_filter,
        'category_filter': category_filter,
    }
    
    return render(request, 'admin_blog_management.html', context)


def admin_blog_detail(request, blog_id):
    blog = get_object_or_404(BlogPost, id=blog_id)
    
    blog_data = {
        'id': blog.id,
        'title': blog.title,
        'content': blog.content,
        'excerpt': blog.excerpt or 'No excerpt available',
        'author_name': blog.author.fname,
        'author_email': blog.author.email,
        'author_field': blog.author.field,
        'category': blog.category.name if blog.category else 'Uncategorized',
        'tags': [tag.name for tag in blog.tags.all()],
        'created_at': blog.created_at.strftime('%B %d, %Y'),
        'updated_at': blog.updated_at.strftime('%B %d, %Y'),
        'published': blog.published,
        'views_count': blog.views_count,
        'likes_count': blog.likes_count(),
        'comments_count': blog.comments_count(),
        'saves_count': blog.saves_count(),
        'image_url': blog.image.url if blog.image else None,
        'status': 'Published' if blog.published else 'Draft'
    }
    
    return HttpResponse(json.dumps(blog_data), content_type='application/json')

def admin_mentorship_management(request):
    if not request.session.get('adminid'):
        return redirect('admin_login')

    mentorship_requests = MentorshipRequest.objects.all().select_related(
        'learner', 'mentor'
    ).order_by('-request_date')

    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('search', '')
    
    if status_filter:
        mentorship_requests = mentorship_requests.filter(status=status_filter)
    
    if search_query:
        mentorship_requests = mentorship_requests.filter(
            Q(learner__name__icontains=search_query) |
            Q(mentor__fname__icontains=search_query) |
            Q(topic__icontains=search_query)
        )

    total_requests = mentorship_requests.count()
    pending_requests = mentorship_requests.filter(status='Pending').count()
    accepted_requests = mentorship_requests.filter(status='Accepted').count()
    declined_requests = mentorship_requests.filter(status='Declined').count()
    
    context = {
        'mentorship_requests': mentorship_requests,
        'total_requests': total_requests,
        'pending_requests': pending_requests,
        'accepted_requests': accepted_requests,
        'declined_requests': declined_requests,
        'status_filter': status_filter,
        'search_query': search_query,
    }
    
    return render(request, 'admin_mentorship_management.html', context)
def admin_mentorship_action(request, request_id):
    mentorship_request = get_object_or_404(MentorshipRequest, id=request_id)
    mentorship_request.delete()
    messages.success(request, 'Mentorship request deleted successfully!')
    return redirect('admin_mentorship_management')

def admin_logout(request):
    if 'adminid' in request.session:
        del request.session['adminid']
        del request.session['adminname']
    return redirect('home')


def submit_report(request):
    if request.method == 'POST':
        try:
            report_type = request.POST.get('report_type')
            title = request.POST.get('title')
            description = request.POST.get('description')
            urgency = request.POST.get('urgency')
            anonymous = request.POST.get('anonymous', False)
            reporter_type = request.POST.get('reporter_type') 
            reporter_id = request.POST.get('reporter_id')

            report = Report(
                report_type=report_type,
                title=title,
                description=description,
                urgency=urgency,
                status='pending'
            )

            if not anonymous:
                if reporter_type == 'retiree':
                    report.reporter_retiree = Retiree.objects.get(id=reporter_id)
                elif reporter_type == 'seeker':
                    report.reporter_seeker = Seeker.objects.get(id=reporter_id)
            
            report.save()
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'message': 'Report submitted successfully!'
                })
            else:
                messages.success(request, 'Report submitted successfully!')
                if reporter_type == 'retiree':
                    return redirect('Rdashboard')
                else:
                    return redirect('Sdashboard')
                
        except Exception as e:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': f'Error submitting report: {str(e)}'
                })
            else:
                messages.error(request, f'Error submitting report: {str(e)}')

                reporter_type = request.POST.get('reporter_type', 'seeker')
                if reporter_type == 'retiree':
                    return redirect('Rdashboard')
                else:
                    return redirect('Sdashboard')

    return redirect('home')


def admin_report_management(request):
    if not request.session.get('adminid'):
        return redirect('admin_login')
    
    try:
        reports = Report.objects.all().select_related('reporter_retiree', 'reporter_seeker').order_by('-created_at')
        
        status_filter = request.GET.get('status', '')
        type_filter = request.GET.get('type', '')
        urgency_filter = request.GET.get('urgency', '')
        search_query = request.GET.get('search', '')
        
        if status_filter:
            reports = reports.filter(status=status_filter)
        
        if type_filter:
            reports = reports.filter(report_type=type_filter)
        
        if urgency_filter:
            reports = reports.filter(urgency=urgency_filter)
        
        if search_query:
            reports = reports.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(reporter_retiree__fname__icontains=search_query) |
                Q(reporter_seeker__name__icontains=search_query)
            )
        

        paginator = Paginator(reports, 10)  
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        total_reports = reports.count()
        pending_reports = reports.filter(status='pending').count()
        in_review_reports = reports.filter(status='in_review').count()
        resolved_reports = reports.filter(status='resolved').count()

        high_urgency = reports.filter(urgency='high').count()
        medium_urgency = reports.filter(urgency='medium').count()
        low_urgency = reports.filter(urgency='low').count()
        
        context = {
            'reports': page_obj,  
            'page_obj': page_obj,  
            'total_reports': total_reports,
            'pending_reports': pending_reports,
            'in_review_reports': in_review_reports,
            'resolved_reports': resolved_reports,
            'high_urgency': high_urgency,
            'medium_urgency': medium_urgency,
            'low_urgency': low_urgency,
            'status_filter': status_filter,
            'type_filter': type_filter,
            'urgency_filter': urgency_filter,
            'search_query': search_query,
            'report_types': Report.REPORT_TYPES,
            'urgency_levels': Report.URGENCY_LEVELS,
            'status_choices': Report.STATUS_CHOICES,
        }
        
        return render(request, 'admin_report_management.html', context)
    
    except Exception as e:
        messages.error(request, f'Error loading reports: {str(e)}')
        return redirect('admin_dashboard')

def admin_report_action(request, report_id, action):
    if not request.session.get('adminid'):
        messages.error(request, 'Please login to access admin panel')
        return redirect('admin_login')
    
    try:
        report = get_object_or_404(Report, id=report_id)
        
        if action == "mark_in_review":
            report.status = 'in_review'
            report.save()
            messages.success(request, f'Report marked as in review.')
        
        elif action == "resolve":
            report.status = 'resolved'
            report.save()
            messages.success(request, f'Report resolved successfully.')
        
        elif action == "reject":
            report.status = 'rejected'  
            report.save()
            messages.success(request, f'Report rejected.')
        
        elif action == "delete":
            report_title = report.title
            report.delete()
            messages.success(request, f'Report "{report_title}" has been deleted successfully!')
        
        else:
            messages.error(request, 'Invalid action')
    
    except Exception as e:
        messages.error(request, f'Error performing action: {str(e)}')
    
    return redirect('admin_report_management')

def admin_report_detail(request, report_id):

    if not request.session.get('adminid'):
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    try:
        report = get_object_or_404(Report, id=report_id)
        
        reporter = report.get_reporter()
        reporter_name = ''
        reporter_email = ''
        reporter_type = ''
        
        if reporter:
            if hasattr(reporter, 'fname'):  
                reporter_name = reporter.fname
                reporter_type = 'retiree'
            elif hasattr(reporter, 'name'): 
                reporter_name = reporter.name
                reporter_type = 'seeker'
            reporter_email = reporter.email
        
        report_data = {
            'id': report.id,
            'title': report.title,
            'description': report.description,
            'report_type': report.get_report_type_display(),
            'urgency': report.get_urgency_display(),
            'status': report.get_status_display(),
            'reporter_name': reporter_name or 'Anonymous',
            'reporter_type': reporter_type or 'anonymous',
            'reporter_email': reporter_email or 'N/A',
            'created_at': report.created_at.strftime('%B %d, %Y at %I:%M %p'),
            'updated_at': report.updated_at.strftime('%B %d, %Y at %I:%M %p'),
            'admin_notes': report.admin_notes or 'No admin notes yet.',
        }
        
        return JsonResponse(report_data)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)