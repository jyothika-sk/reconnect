from django.db import models
from django.utils.text import slugify
from django.contrib.postgres.fields import ArrayField


class Retiree(models.Model):
    fname = models.CharField(max_length=100)
    email = models.EmailField(unique=True)   
    phone = models.CharField(max_length=150)
    password = models.CharField(max_length=100)
    field = models.CharField(max_length=150)
    experience = models.CharField(max_length=100)
    bio = models.CharField(max_length=200)
    proof = models.FileField(upload_to='proof/')
    photo = models.ImageField(upload_to='photo/')
    mentorship = models.CharField(max_length=150)
    other_area = models.CharField(max_length=150, blank=True, null=True)  
    role = models.CharField(max_length=50, default="Retiree")
    skills = models.TextField(help_text="Comma separated list of skills", blank=True, null=True)
    avilabilty  = models.CharField(max_length=20,choices=[("Morning", "Morning"), ("Evening", "Evening")],default="pending")
    is_approved = models.BooleanField(default=False, verbose_name="Approved by Admin")
    def skill_list(self):
        return [skill.strip() for skill in self.skills.split(',')] if self.skills else []


    def __str__(self):
        return self.fname

class Seeker(models.Model):
    name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)  
    interests = models.TextField(blank=True, null=True)
    goals = models.TextField(blank=True, null=True)
    photo = models.ImageField(upload_to='seeker_photos/', blank=True, null=True)

    def __str__(self):
        return self.name
    
class FollowRequest(models.Model):
    seeker = models.ForeignKey("Seeker", on_delete=models.CASCADE)
    retiree = models.ForeignKey("Retiree", on_delete=models.CASCADE)
    status = models.CharField(
        max_length=20,
        choices=[("pending", "Pending"), ("accepted", "Accepted"), ("rejected", "Rejected")],
        default="pending"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.seeker.name} → {self.retiree.fname} ({self.status})"

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
class BlogPost(models.Model):
    author = models.ForeignKey('Retiree', on_delete=models.CASCADE, related_name='posts')
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    content = models.TextField()
    excerpt = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='blog_images/', blank=True, null=True, max_length=300)
    published = models.BooleanField(default=False)
    views_count = models.PositiveIntegerField(default=0)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    tags = models.ManyToManyField(Tag, blank=True)
    
    likes = models.ManyToManyField('Seeker', blank=True, related_name='liked_blogs')
    saves = models.ManyToManyField('Seeker', blank=True, related_name='saved_blogs')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def likes_count(self):
        return self.likes.count()

    def saves_count(self):
        return self.saves.count()

    def comments_count(self):
        return self.comments.count()  

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:200]
            slug = base
            n = 1
            while BlogPost.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title
    

class BlogComment(models.Model):
    post = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey('Seeker', on_delete=models.CASCADE)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.name} on {self.post.title}"

    
class MentorshipRequest(models.Model):
    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Accepted", "Accepted"),
        ("Declined", "Declined"),
    ]

    learner = models.ForeignKey("Seeker", on_delete=models.CASCADE)
    mentor = models.ForeignKey("Retiree", on_delete=models.CASCADE)
    topic = models.CharField(max_length=150)
    message = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")
    request_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.learner.name} → {self.mentor.fname} ({self.topic})"


class AdminUser(models.Model):
    username = models.CharField(max_length=50, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=50)  
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.username
    
class SavedBlog(models.Model):
    seeker = models.ForeignKey(Seeker, on_delete=models.CASCADE, related_name='saved_blog_posts',null=True,blank=True)
    blog = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name='saved_by')
    saved_at = models.DateTimeField(auto_now_add=True)
    

    class Meta:
        unique_together = ('seeker', 'blog')  
        ordering = ['-saved_at']

    def __str__(self):
        return f"{self.seeker.name} saved {self.blog.title}"


class Message(models.Model):
    SENDER_TYPE_CHOICES = [
        ('seeker', 'Seeker'),
        ('retiree', 'Retiree'),
    ]
    
    sender_seeker = models.ForeignKey(Seeker, on_delete=models.CASCADE, null=True, blank=True, related_name='sent_messages')
    sender_retiree = models.ForeignKey(Retiree, on_delete=models.CASCADE, null=True, blank=True, related_name='sent_messages')
    receiver_seeker = models.ForeignKey(Seeker, on_delete=models.CASCADE, null=True, blank=True, related_name='received_messages')
    receiver_retiree = models.ForeignKey(Retiree, on_delete=models.CASCADE, null=True, blank=True, related_name='received_messages')
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def get_sender(self):
        return self.sender_seeker or self.sender_retiree
    
    def get_receiver(self):
        return self.receiver_seeker or self.receiver_retiree
    
    def get_sender_type(self):
        if self.sender_seeker:
            return 'seeker'
        elif self.sender_retiree:
            return 'retiree'
        return None
    
    def get_receiver_type(self):
        if self.receiver_seeker:
            return 'seeker'
        elif self.receiver_retiree:
            return 'retiree'
        return None
    
    def __str__(self):
        return f"{self.get_sender()} -> {self.get_receiver()}: {self.content}"
    

class RetireeBlogComment(models.Model):
    post = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name='Retireecomments') 
    retiree = models.ForeignKey(Retiree, on_delete=models.CASCADE, null=True, blank=True)  
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.retiree:
            return f"Comment by {self.retiree.fname} on {self.post.title}"
        else:
            return f"Comment by {self.user.name} on {self.post.title}"

class RetireeSavedBlog(models.Model):
    seeker = models.ForeignKey(Seeker, on_delete=models.CASCADE, related_name='retiree_saved_blog_posts', null=True, blank=True)
    retiree = models.ForeignKey(Retiree, on_delete=models.CASCADE, related_name='retiree_saved_blog_posts', null=True, blank=True)
    blog = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name='retiree_saved_by')
    saved_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('seeker', 'blog')  
        ordering = ['-saved_at']

    def __str__(self):
        if self.retiree:
            return f"{self.retiree.fname} saved {self.blog.title}"
        else:
            return f"{self.seeker.name} saved {self.blog.title}"
        

class Report(models.Model):
    REPORT_TYPES = [
        ('technical', 'Technical Issue'),
        ('harassment', 'Harassment/Bullying'),
        ('inappropriate_content', 'Inappropriate Content'),
        ('spam', 'Spam or Scam'),
        ('bug', 'Website Bug'),
        ('suggestion', 'Feature Suggestion'),
        ('other', 'Other'),
    ]
    
    URGENCY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_review', 'In Review'),
        ('resolved', 'Resolved'),
        ('rejected', 'Rejected'),
    ]
    
    reporter_retiree = models.ForeignKey(Retiree, on_delete=models.SET_NULL, null=True, blank=True, related_name='reports_submitted')
    reporter_seeker = models.ForeignKey(Seeker, on_delete=models.SET_NULL, null=True, blank=True, related_name='reports_submitted')
    
    report_type = models.CharField(max_length=50, choices=REPORT_TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    urgency = models.CharField(max_length=10, choices=URGENCY_LEVELS, default='low')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    admin_notes = models.TextField(blank=True)
    
    def get_reporter(self):
        return self.reporter_retiree or self.reporter_seeker
    
    def get_reporter_type(self):
        if self.reporter_retiree:
            return 'retiree'
        elif self.reporter_seeker:
            return 'seeker'
        return 'anonymous'
    
    def __str__(self):
        reporter_name = "Anonymous"
        if self.reporter_retiree:
            reporter_name = self.reporter_retiree.fname
        elif self.reporter_seeker:
            reporter_name = self.reporter_seeker.name
        return f"{self.title} - {self.get_report_type_display()} (by {reporter_name})"