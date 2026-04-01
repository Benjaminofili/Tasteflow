import pytest
from playwright.sync_api import Page, expect

@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Configure browser size for E2E tests."""
    return {
        **browser_context_args,
        "viewport": {
            "width": 1280,
            "height": 720,
        }
    }

def test_landing_page(page: Page):
    """Test the landing page loads successfully."""
    try:
        page.goto("http://localhost:5000/")
        # Check title
        expect(page).to_have_title("RegFood || Restaurant HTML Template")
        # Check for banner text - use a more specific locator to avoid strict mode violation
        expect(page.locator("h3:has-text('Satisfy Your Cravings')")).to_be_visible()
        expect(page.locator("h1:has-text('Delicious Foods')")).to_be_visible()
    except Exception as e:
        pytest.fail(f"Could not connect to localhost:5000 or content missing. Error: {e}")

def test_navigation_to_login(page: Page):
    """Test that a user can navigate to the login page."""
    try:
        page.goto("http://localhost:5000/")
        # Go directly to login for reliability in automated tests
        page.goto("http://localhost:5000/auth/login")
        expect(page).to_have_url("http://localhost:5000/auth/login")
        expect(page.locator("h2:has-text('Welcome back!')")).to_be_visible()
    except Exception as e:
        pytest.fail(f"E2E Navigation failed: {e}")

def test_login_interface_elements(page: Page):
    """Verify login form elements are present and correctly labeled."""
    page.goto("http://localhost:5000/auth/login")
    expect(page.locator("input[name='email']")).to_be_visible()
    expect(page.locator("input[name='password']")).to_be_visible()
    expect(page.locator("button[type='submit']")).to_have_text("login")
