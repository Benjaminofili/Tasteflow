import cloudinary
import cloudinary.uploader
from flask import current_app
from werkzeug.utils import secure_filename
import os
import re

ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'webm', 'mov', 'avi', 'mkv'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

class FileUploadError(Exception):
    """Custom exception for file upload errors."""
    pass

def allowed_file(filename, file_type='image'):
    """Check if file extension is allowed."""
    if not filename or '.' not in filename:
        return False
    
    ext = filename.rsplit('.', 1)[1].lower()
    
    if file_type == 'image':
        return ext in ALLOWED_IMAGE_EXTENSIONS
    elif file_type == 'video':
        return ext in ALLOWED_VIDEO_EXTENSIONS
    
    return False

def validate_file_size(file):
    """Check if file size is within limits."""
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)  # Reset file pointer
    return size <= MAX_FILE_SIZE

def upload_file_to_cloudinary(file, resource_type="image"):
    """
    Upload file to Cloudinary with comprehensive validation.
    """
    if not file or file.filename == '':
        return None
    
    # Secure the filename
    filename = secure_filename(file.filename)
    
    # Validate file type
    if resource_type == "image":
        if not allowed_file(filename, 'image'):
            raise FileUploadError(
                f"Invalid image file. Allowed formats: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"
            )
    elif resource_type == "video":
        if not allowed_file(filename, 'video'):
            raise FileUploadError(
                f"Invalid video file. Allowed formats: {', '.join(ALLOWED_VIDEO_EXTENSIONS)}"
            )
    
    # Validate file size
    if not validate_file_size(file):
        raise FileUploadError(f"File too large. Maximum size: {MAX_FILE_SIZE / (1024*1024):.0f}MB")
    
    try:
        # Upload to Cloudinary with timeout
        upload_params = {
            'resource_type': 'auto' if resource_type == 'video' else 'image',
            'folder': 'food_ordering',
            'timeout': 15,
        }
        
        # Add transformations for images
        if resource_type == 'image':
            upload_params['transformation'] = [
                {'width': 1200, 'height': 1200, 'crop': 'limit'},
                {'quality': 'auto:good'},
            ]
        
        result = cloudinary.uploader.upload(file, **upload_params)
        return result.get('secure_url')
        
    except cloudinary.exceptions.Error as e:
        current_app.logger.error(f"Cloudinary error: {e}")
        raise FileUploadError("Failed to upload file to cloud storage")
    except Exception as e:
        current_app.logger.error(f"Unexpected upload error: {e}")
        raise FileUploadError("An unexpected error occurred during upload")

def delete_file_from_cloudinary(url):
    """Delete file from Cloudinary by URL."""
    if not url:
        return False
    
    try:
        parts = url.split('/')
        if 'food_ordering' in parts:
            idx = parts.index('food_ordering')
            public_id_with_ext = '/'.join(parts[idx:])
            public_id = public_id_with_ext.rsplit('.', 1)[0]
            
            cloudinary.uploader.destroy(public_id)
            return True
    except Exception as e:
        current_app.logger.error(f"Error deleting from Cloudinary: {e}")
        return False

def sanitize_filename(filename):
    """Remove unsafe characters from filename."""
    filename = os.path.basename(filename)
    filename = re.sub(r'[^\w\s.-]', '', filename)
    filename = re.sub(r'\s+', '_', filename)
    return filename[:255]

def format_currency(amount):
    """Format amount as currency."""
    try:
        return f"${float(amount):.2f}"
    except (ValueError, TypeError):
        return "$0.00"

def validate_email(email):
    """Basic email validation."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_phone(phone):
    """Validate phone number format."""
    cleaned = re.sub(r'\D', '', phone)
    return len(cleaned) >= 10

def generate_order_number():
    """Generate unique order number."""
    import random
    import string
    from datetime import datetime
    date_part = datetime.now().strftime('%Y%m%d')
    random_part = ''.join(random.choices(string.digits, k=5))
    return f"ORD-{date_part}-{random_part}"

def serialize_order_event(order):
    """Serialize order for JSON API responses - used by admin, customer, and owner"""
    status = (order.status or '').strip().lower()
    status_map = {
        'pending': ('Pending', 'warning', 'placed'),
        'accepted': ('Accepted', 'info', 'accepted'),
        'preparing': ('Preparing', 'info', 'preparing'),
        'out for delivery': ('Out for Delivery', 'primary', 'en_route'),
        'delivered': ('Delivered', 'success', 'delivered'),
        'completed': ('Completed', 'success', 'completed'),
        'cancelled': ('Cancelled', 'danger', 'cancelled'),
    }
    label, tone, timeline_key = status_map.get(
        status, 
        (status.title() if status else 'Unknown', 'secondary', 'unknown')
    )
    
    return {
        'id': order.id,
        'status': status,
        'status_label': label,
        'status_tone': tone,
        'timeline_key': timeline_key,
        'delivery_time': order.delivery_time.strftime('%I:%M %p') if order.delivery_time else None,
        'total_amount': float(order.total_amount),
        'order_date': order.order_date.isoformat() if order.order_date else None,
        'customer_name': order.customer.name if order.customer else 'Customer',
        'restaurant_name': order.restaurant.name if order.restaurant else 'Restaurant'
    }

def is_ajax_request(request):
    """Detect if request is AJAX/JSON"""
    return (
        request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
        request.headers.get('Accept') == 'application/json' or
        (request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html)
    )
