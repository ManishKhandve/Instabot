import asyncio
import random
import json
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import tkinter as tk
from tkinter import messagebox, ttk, scrolledtext
import subprocess
import sys

# ==================== CONFIGURATION ====================
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
COOKIES_FILE = "instagram_cookies.json"
# =======================================================


class InstagramCommenter:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
    
    async def start_browser(self):
        """Initialize browser with realistic settings"""
        print("🚀 Starting browser...")
        playwright = await async_playwright().start()
        # Try to launch the browser. If the playwright browser binaries are missing
        # (common after a fresh install or when running a frozen exe without preinstalled browsers),
        # attempt to automatically install them and retry once.
        try:
            self.browser = await playwright.chromium.launch(
                headless=False,
                args=['--disable-blink-features=AutomationControlled']
            )
        except Exception as e:
            msg = str(e).lower()
            if 'executable' in msg and ('doesn' in msg or 'does not' in msg or "doesn't" in msg):
                print("⚠️ Playwright browser executable not found. Attempting to run 'playwright install chromium'...")
                try:
                    # Use the same Python interpreter to run the Playwright installer
                    subprocess.run([sys.executable, '-m', 'playwright', 'install', 'chromium'], check=False)
                    print("⬇️ Browser install attempted — retrying browser launch...")
                    self.browser = await playwright.chromium.launch(
                        headless=False,
                        args=['--disable-blink-features=AutomationControlled']
                    )
                except Exception as e2:
                    print(f"❌ Still failed to start browser after installing: {e2}")
                    raise
            else:
                raise
        
        # Create context with user agent
        self.context = await self.browser.new_context(
            user_agent=USER_AGENT,
            viewport={'width': 1920, 'height': 1080}
        )
        
        # Avoid detection
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        self.page = await self.context.new_page()
        print("✅ Browser started successfully")
    
    async def load_cookies(self):
        """Load cookies from file if exists"""
        if Path(COOKIES_FILE).exists():
            print("🍪 Loading saved cookies...")
            with open(COOKIES_FILE, 'r') as f:
                cookies = json.load(f)
                await self.context.add_cookies(cookies)
            print("✅ Cookies loaded successfully")
            return True
        return False
    
    async def save_cookies(self):
        """Save cookies to file"""
        print("💾 Saving cookies...")
        cookies = await self.context.cookies()
        with open(COOKIES_FILE, 'w') as f:
            json.dump(cookies, f, indent=2)
        print("✅ Cookies saved successfully")
    
    async def login(self, force_new_login=False):
        """Login to Instagram with cookie persistence"""
        print("🔐 Attempting to login...")
        
        # Delete cookies if force new login
        if force_new_login and Path(COOKIES_FILE).exists():
            print("🗑️ Deleting saved cookies for new login...")
            Path(COOKIES_FILE).unlink()
        
        # Try loading cookies first
        cookies_loaded = await self.load_cookies()
        
        await self.page.goto("https://www.instagram.com/", wait_until="networkidle")
        await asyncio.sleep(random.uniform(1, 2))
        
        # Check if already logged in
        if cookies_loaded:
            await self.page.reload(wait_until="networkidle")
            await asyncio.sleep(1)
            
            # Check if login was successful
            try:
                await self.page.wait_for_selector('svg[aria-label="Home"]', timeout=3000)
                print("✅ Already logged in via cookies")
                return True
            except PlaywrightTimeoutError:
                print("⚠️ Cookies expired, logging in manually...")
        
        # Manual login
        print("📝 Please login manually in the browser...")
        print("⏳ Waiting for manual login (checking for home icon)...")
        
        try:
            # Wait for the user to login manually
            await self.page.wait_for_selector('svg[aria-label="Home"]', timeout=600000)  # 10 minutes
            print("✅ Login successful!")
            
            # Save cookies for future use
            await self.save_cookies()
            return True
            
        except PlaywrightTimeoutError:
            print("❌ Login timeout - please try again")
            return False
    
    async def post_comment(self, comment_text):
        """Post a single comment - always click and focus before paste, with human-like actions and selector fallback"""
        try:
            print(f"💬 Posting comment: '{comment_text}'")
            
            # Human-like mouse movement and scroll before interacting
            await self.page.mouse.move(random.randint(200, 800), random.randint(200, 600))
            await asyncio.sleep(random.uniform(0.3, 0.7))
            await self.page.evaluate("window.scrollBy(0, arguments[0])", random.randint(100, 400))
            await asyncio.sleep(random.uniform(0.3, 0.7))
            
            # Find comment box
            comment_box = None
            selectors = [
                'textarea[aria-label="Add a comment…"]',
                'textarea[placeholder="Add a comment…"]',
                'textarea[aria-label="Add a comment..."]'
            ]
            
            for selector in selectors:
                try:
                    comment_box = await self.page.wait_for_selector(selector, timeout=3000)
                    if comment_box:
                        # Focus the comment box after clicking
                        await comment_box.click()
                        await self.page.focus(selector)
                        await asyncio.sleep(0.2)
                        break
                except PlaywrightTimeoutError:
                    continue
            
            # Fallback: XPath for textarea with 'comment' in placeholder
            if not comment_box:
                try:
                    comment_box = await self.page.wait_for_selector('//textarea[contains(@placeholder, "comment")]', timeout=3000)
                    if comment_box:
                        await comment_box.click()
                        await asyncio.sleep(0.2)
                except PlaywrightTimeoutError:
                    pass
            
            if not comment_box:
                raise Exception("Could not find comment box")
            
            # Clear any existing text first
            await comment_box.fill('')
            await asyncio.sleep(0.1)
            
            # Paste the comment directly (instant)
            print("📋 Pasting comment...")
            await comment_box.fill(comment_text)
            await asyncio.sleep(0.3)
            
            # Find and click Post button - try multiple methods
            print("🔍 Looking for Post button...")
            
            # Method 1: Try visible Post button with text
            try:
                post_button = await self.page.wait_for_selector('button:has-text("Post")', timeout=2000, state='visible')
                if post_button:
                    await post_button.click()
                    print("✅ Clicked Post button (method 1)")
                    await asyncio.sleep(1)
                    return True
            except:
                pass
            
            # Method 2: Try div with role button and Post text
            try:
                post_button = await self.page.wait_for_selector('div[role="button"]:has-text("Post")', timeout=2000, state='visible')
                if post_button:
                    await post_button.click()
                    print("✅ Clicked Post button (method 2)")
                    await asyncio.sleep(1)
                    return True
            except:
                pass
            
            # Method 3: Press Enter key as alternative
            try:
                print("⌨️ Trying Enter key...")
                await comment_box.press('Enter')
                await asyncio.sleep(1.5)
                print("✅ Pressed Enter to post")
                return True
            except:
                pass
            
            raise Exception("Could not find or click Post button")
            
        except Exception as e:
            print(f"❌ Failed to post comment: {str(e)}")
            return False
    
    async def comment_on_post(self, post_url, comments_list, comment_count):
        """Navigate to post and make comments"""
        try:
            print(f"🌐 Navigating to post: {post_url}")
            await self.page.goto(post_url, wait_until="networkidle")
            await asyncio.sleep(random.uniform(2, 3))
            
            print(f"📝 Starting to post {comment_count} comment(s)...")
            print(f"📋 Available comments: {comments_list}")
            
            successful_comments = 0
            for i in range(comment_count):
                print(f"\n{'='*50}")
                print(f"--- Posting Comment {i + 1}/{comment_count} ---")
                print(f"{'='*50}")
                
                # Refresh page after first comment to avoid issues
                if i > 0:
                    print("🔄 Refreshing page for next comment...")
                    await self.page.reload(wait_until="networkidle")
                    await asyncio.sleep(random.uniform(2, 3))
                
                # Select random comment from user's list
                comment_text = random.choice(comments_list)
                print(f"🎲 Selected comment: '{comment_text}'")
                
                # Post comment
                success = await self.post_comment(comment_text)
                
                if success:
                    successful_comments += 1
                    print(f"✅ Successfully posted {successful_comments}/{comment_count}")
                else:
                    print(f"❌ Failed to post comment {i + 1}")
                
                # Wait before next comment
                if i < comment_count - 1:
                    # Add longer delay after every 3 comments
                    if (i + 1) % 3 == 0:
                        delay = random.uniform(10, 20)  # Longer delay every 3 comments
                        print(f"⏸️  BREAK TIME after 3 comments!")
                        print(f"⏳ Waiting {delay:.1f} seconds (longer break)...")
                    else:
                        delay = random.uniform(3, 6)  # Regular delay
                        print(f"⏳ Waiting {delay:.1f} seconds before next comment...")
                    
                    await asyncio.sleep(delay)
            
            print(f"\n{'='*50}")
            print(f"✅ COMPLETED! {successful_comments}/{comment_count} comments posted successfully")
            print(f"{'='*50}")
            return successful_comments
            
        except Exception as e:
            print(f"❌ Error during commenting: {str(e)}")
            return 0
    
    async def close(self):
        """Close browser"""
        if self.browser:
            print("🔒 Closing browser...")
            await self.browser.close()
            print("✅ Browser closed")


class CommentBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Instagram Comment Bot")
        self.root.geometry("650x650")
        self.root.resizable(False, False)
        
        # Stop flag
        self.should_stop = False
        self.bot_instance = None
        
        # Style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Main frame with scrollbar
        canvas = tk.Canvas(root)
        scrollbar = ttk.Scrollbar(root, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, padding="20")
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        main_frame = scrollable_frame
        
        # Title
        title = ttk.Label(main_frame, text="Instagram Comment Bot", font=('Arial', 16, 'bold'))
        title.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Login option
        ttk.Label(main_frame, text="Login Option:", font=('Arial', 10, 'bold')).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.new_login_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(main_frame, text="Login with different account (delete saved cookies)", 
                       variable=self.new_login_var).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(0, 15))
        
        # Post URL
        ttk.Label(main_frame, text="Post URL:", font=('Arial', 10)).grid(row=3, column=0, sticky=tk.W, pady=5)
        self.url_entry = ttk.Entry(main_frame, width=70)
        self.url_entry.grid(row=4, column=0, columnspan=2, pady=(0, 15))
        
        # Comments selection
        ttk.Label(main_frame, text="Select Comments to Use:", font=('Arial', 10, 'bold')).grid(row=5, column=0, sticky=tk.W, pady=5)
        
        # Default comments with checkboxes
        comments_frame = ttk.Frame(main_frame)
        comments_frame.grid(row=6, column=0, columnspan=2, sticky=tk.W, pady=(0, 15))
        
        self.default_comments = [
            "Nice!",
            "Awesome post!",
            "🔥🔥",
            "Cool!",
            "Love this! ❤️",
            "Amazing!",
            "Great content!",
            "👏👏👏",
            "So good!",
            "Incredible! 😍"
        ]
        
        self.comment_vars = []
        for i, comment in enumerate(self.default_comments):
            var = tk.BooleanVar(value=False)  # Start unchecked
            self.comment_vars.append(var)
            cb = ttk.Checkbutton(comments_frame, text=comment, variable=var)
            cb.grid(row=i//2, column=i%2, sticky=tk.W, padx=10, pady=2)
        
        # Custom comment
        ttk.Label(main_frame, text="Custom Comment (optional):", font=('Arial', 10, 'bold')).grid(row=7, column=0, sticky=tk.W, pady=(15, 5))
        self.custom_comment_entry = ttk.Entry(main_frame, width=70)
        self.custom_comment_entry.grid(row=8, column=0, columnspan=2, pady=(0, 5))
        
        self.custom_comment_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(main_frame, text="Use custom comment", 
                       variable=self.custom_comment_var).grid(row=9, column=0, columnspan=2, sticky=tk.W, pady=(0, 15))
        
        # Comment count
        ttk.Label(main_frame, text="Number of Comments to Post:", font=('Arial', 10)).grid(row=10, column=0, sticky=tk.W, pady=5)
        self.count_entry = ttk.Entry(main_frame, width=20)
        self.count_entry.grid(row=11, column=0, columnspan=2, sticky=tk.W, pady=(0, 20))
        self.count_entry.insert(0, "2")
        
        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=12, column=0, columnspan=2, pady=10)
        
        self.start_button = ttk.Button(buttons_frame, text="Start Bot", command=self.start_bot)
        self.start_button.grid(row=0, column=0, padx=5)
        
        self.stop_button = ttk.Button(buttons_frame, text="Stop Bot", command=self.stop_bot, state='disabled')
        self.stop_button.grid(row=0, column=1, padx=5)
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="Ready", foreground="green", font=('Arial', 9))
        self.status_label.grid(row=13, column=0, columnspan=2, pady=5)
        
    def start_bot(self):
        """Validate inputs and start the bot in a thread for GUI responsiveness"""
        url = self.url_entry.get().strip()
        count_str = self.count_entry.get().strip()
        
        # Validation
        if not url:
            messagebox.showerror("Error", "Please enter a post URL")
            return
        
        if not url.startswith("https://www.instagram.com/"):
            messagebox.showerror("Error", "Please enter a valid Instagram URL")
            return
        
        # Build comments list from selected checkboxes
        comments_list = []
        for i, var in enumerate(self.comment_vars):
            if var.get():
                comments_list.append(self.default_comments[i])
        # Add custom comment if selected
        custom_comment_selected = self.custom_comment_var.get()
        custom_comment = self.custom_comment_entry.get().strip()
        if custom_comment_selected and custom_comment:
            comments_list.append(custom_comment)
        # If only custom comment is selected, use it for all comments
        if custom_comment_selected and not any(var.get() for var in self.comment_vars) and custom_comment:
            comments_list = [custom_comment]

        if not comments_list:
            messagebox.showerror("Error", "Please select at least one comment or add a custom comment")
            return
        
        try:
            count = int(count_str)
            if count < 1 or count > 100:
                messagebox.showerror("Error", "Please enter a number between 1 and 100")
                return
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number")
            return
        
        # Check new login option
        force_new_login = self.new_login_var.get()
        
        print(f"\n📋 Selected {len(comments_list)} comment(s) to randomly choose from")
        print(f"🎯 Will post {count} comment(s) total")
        
        # Reset stop flag
        self.should_stop = False
        
        # Disable start button, enable stop button
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.status_label.config(text="Running... Check console for details", foreground="orange")
        
        # Print selected comments for debugging
        print(f"\n📋 Comments to use: {comments_list}")
        
        # Run bot in a separate thread
        import threading
        threading.Thread(target=lambda: asyncio.run(self.run_bot(url, comments_list, count, force_new_login)), daemon=True).start()

    def stop_bot(self):
        """Stop the bot"""
        self.should_stop = True
        print("\n🛑 STOP requested by user!")
        self.status_label.config(text="Stopping...", foreground="red")
        if self.bot_instance:
            asyncio.create_task(self.bot_instance.close())
    
    async def run_bot(self, url, comments_list, count, force_new_login):
        """Run the Instagram bot"""
        self.bot_instance = InstagramCommenter()
        
        try:
            await self.bot_instance.start_browser()
            
            # Login
            login_success = await self.bot_instance.login(force_new_login=force_new_login)
            
            if not login_success:
                messagebox.showerror("Error", "Login failed. Please check console.")
                return
            
            # Comment on post with stop check
            await self.comment_on_post_with_stop(url, comments_list, count)
            
            if not self.should_stop:
                messagebox.showinfo("Success", f"Bot completed! Check console for details.")
            else:
                messagebox.showinfo("Stopped", "Bot stopped by user.")
            
        except Exception as e:
            print(f"❌ Fatal error: {str(e)}")
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
        
        finally:
            await self.bot_instance.close()
            self.bot_instance = None
    
    async def comment_on_post_with_stop(self, url, comments_list, count):
        """Comment with stop check and immediate stop during delays"""
        try:
            print(f"🌐 Navigating to post: {url}")
            await self.bot_instance.page.goto(url, wait_until="networkidle")
            await asyncio.sleep(random.uniform(2, 3))
            
            print(f"📝 Starting to post {count} comment(s)...")
            
            successful_comments = 0
            for i in range(count):
                if self.should_stop:
                    print("\n🛑 Bot stopped by user!")
                    break
                
                print(f"\n{'='*50}")
                print(f"--- Posting Comment {i + 1}/{count} ---")
                print(f"{'='*50}")
                
                # Select random comment
                comment_text = random.choice(comments_list)
                print(f"🎲 Selected comment: '{comment_text}'")
                
                # Post comment
                success = await self.bot_instance.post_comment(comment_text)
                
                if success:
                    successful_comments += 1
                    print(f"✅ Successfully posted {successful_comments}/{count}")
                else:
                    print(f"❌ Failed to post comment {i + 1}")
                    print("🔄 Refreshing page after failed comment...")
                    await self.bot_instance.page.reload(wait_until="networkidle")
                    await asyncio.sleep(random.uniform(2, 3))
                
                # Wait before next comment, with immediate stop check
                if i < count - 1 and not self.should_stop:
                    if (i + 1) % 3 == 0:
                        delay = random.uniform(10, 20)
                        print(f"⏸️  BREAK TIME after 3 comments!")
                        print(f"⏳ Waiting {delay:.1f} seconds (longer break)...")
                    else:
                        delay = random.uniform(3, 6)
                        print(f"⏳ Waiting {delay:.1f} seconds before next comment...")
                    # Split delay into 0.5s chunks for immediate stop
                    waited = 0
                    while waited < delay:
                        if self.should_stop:
                            print("\n🛑 Bot stopped by user during delay!")
                            break
                        chunk = min(0.5, delay - waited)
                        await asyncio.sleep(chunk)
                        waited += chunk
                    if self.should_stop:
                        break
            
            print(f"\n{'='*50}")
            print(f"✅ COMPLETED! {successful_comments}/{count} comments posted successfully")
            print(f"{'='*50}")
            
        except Exception as e:
            print(f"❌ Error during commenting: {str(e)}")


def main():
    """Main entry point"""
    print("=" * 50)
    print("Instagram Comment Bot - Enhanced Version")
    print("=" * 50)
    
    # Create GUI
    root = tk.Tk()
    app = CommentBotGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
