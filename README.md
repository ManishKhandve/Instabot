# Instagram Comment Bot

Automate posting comments on Instagram posts using a user-friendly desktop GUI.

## Features
- Login to Instagram with cookie persistence
- Select or enter custom comments
- Specify the number of comments to post
- Human-like browser automation using Playwright
- GUI built with Tkinter
- Option to stop the bot at any time

## Requirements
- Python 3.8+
- Playwright
- Tkinter

## Installation
1. Clone this repository:
   ```sh
   git clone https://github.com/your-username/your-repo-name.git
   cd your-repo-name
   ```
2. Install dependencies:
   ```sh
   pip install -r requirements.txt
   python -m playwright install
   ```

## Usage
Run the bot:
```sh
python insta.py
```

A GUI window will appear. Enter the Instagram post URL, select comments, set the number of comments, and start the bot.

## Notes
- The bot uses Playwright for browser automation. The first run may download browser binaries.
- Login is handled via cookies for convenience. You can force a new login if needed.
- Use responsibly and respect Instagram's terms of service.

