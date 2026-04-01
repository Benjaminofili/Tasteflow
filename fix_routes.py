import os
import re
import glob

base_dir = r"c:/Users/benja/onedrive2/OneDrive/Desktop/Semester 4/Take2"

# 1. Update owner.py routes
owner_py_full = os.path.join(base_dir, "app/routes/owner.py")
with open(owner_py_full, "r", encoding="utf-8") as f:
    content = f.read()

# Prefix @bp.route('/...') with /api/ if not already /api/
content = re.sub(r"@bp\.route\('/(?!api/)", r"@bp.route('/api/", content)
with open(owner_py_full, "w", encoding="utf-8") as f:
    f.write(content)


# 2. Update HTML templates
templates_dir = os.path.join(base_dir, "app/templates/owner")
html_files = glob.glob(os.path.join(templates_dir, "*.html"))

for html_file in html_files:
    with open(html_file, "r", encoding="utf-8") as f:
        html = f.read()
    
    # Replace fetch calls
    html = re.sub(r"fetch\('/owner/(?!api/)", r"fetch('/owner/api/", html)
    
    # Fix media/add path which should post to /api/media
    html = html.replace("fetch('/owner/api/media/add'", "fetch('/owner/api/media'")
    
    # Check if we need to insert Coupons link
    # We look for the closing </a> of Upload Menu
    if "Upload Menu" in html and "Coupons" not in html[html.find("Upload Menu") : html.find("Upload Menu")+400]:
        coupon_link = """
            </a>
            <a href="/owner/coupons" class="flex items-center gap-3 px-4 py-3 text-gray-600 hover:bg-gray-50 hover:text-charcoal rounded-xl font-medium transition-colors">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 5v2m0 4v2m0 4v2M5 5a2 2 0 00-2 2v3a2 2 0 110 4v3a2 2 0 002 2h14a2 2 0 002-2v-3a2 2 0 110-4V7a2 2 0 00-2-2H5z"></path></svg>
                Coupons
            </a>"""
            
        html = re.sub(r"Upload Menu[\s\n]*</a>", "Upload Menu" + coupon_link, html)
        
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html)
        
print("Updated API routes and fetch calls successfully.")
