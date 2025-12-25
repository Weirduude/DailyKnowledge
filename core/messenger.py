"""
Email messenger module.
Handles rendering markdown to HTML and sending via SMTP.
"""

import smtplib
from smtplib import SMTPResponseException
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

import markdown
from premailer import transform

import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    SMTP_SERVER,
    SMTP_PORT,
    SMTP_USERNAME,
    SMTP_PASSWORD,
    EMAIL_FROM,
    EMAIL_TO,
    CATEGORIES,
)


# Inline CSS for email compatibility
EMAIL_STYLES = """
<style>
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    line-height: 1.6;
    color: #333;
    max-width: 700px;
    margin: 0 auto;
    padding: 20px;
    background-color: #f5f5f5;
}
.container {
    background-color: #ffffff;
    border-radius: 8px;
    padding: 30px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}
h1 {
    color: #1a73e8;
    border-bottom: 2px solid #1a73e8;
    padding-bottom: 10px;
}
h2 {
    color: #34a853;
    margin-top: 30px;
}
h3 {
    color: #5f6368;
    margin-top: 20px;
}
.category-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 16px;
    font-size: 14px;
    font-weight: 500;
    margin-bottom: 15px;
}
.category-Foundations { background-color: #e6f4ea; color: #137333; }
.category-Engineering { background-color: #e8f0fe; color: #1967d2; }
.category-SOTA { background-color: #f3e8fd; color: #8430ce; }
.category-Reasoning { background-color: #fef7e0; color: #b06000; }
.category-History { background-color: #fff8e1; color: #f9a825; }
pre {
    background-color: #f8f9fa;
    border: 1px solid #e8eaed;
    border-radius: 8px;
    padding: 16px;
    overflow-x: auto;
    font-size: 14px;
}
code {
    font-family: 'Fira Code', 'Monaco', 'Consolas', monospace;
    background-color: #f1f3f4;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 0.9em;
}
pre code {
    background-color: transparent;
    padding: 0;
}
blockquote {
    border-left: 4px solid #1a73e8;
    margin: 16px 0;
    padding-left: 16px;
    color: #5f6368;
}
.review-section {
    background-color: #fff8e1;
    border-left: 4px solid #f9a825;
    padding: 16px;
    margin: 20px 0;
    border-radius: 0 8px 8px 0;
}
.new-section {
    background-color: #e8f5e9;
    border-left: 4px solid #34a853;
    padding: 16px;
    margin: 20px 0;
    border-radius: 0 8px 8px 0;
}
.footer {
    margin-top: 30px;
    padding-top: 20px;
    border-top: 1px solid #e8eaed;
    color: #5f6368;
    font-size: 12px;
    text-align: center;
}
details {
    background-color: #f8f9fa;
    border: 1px solid #e8eaed;
    border-radius: 8px;
    padding: 12px;
    margin: 10px 0;
}
summary {
    cursor: pointer;
    color: #1a73e8;
    font-weight: 500;
}
.stats {
    margin: 20px 0;
    padding: 15px;
    background-color: #f8f9fa;
    border-radius: 8px;
}
.stats table {
    width: 100%;
    border-collapse: collapse;
}
.stat-item {
    text-align: center;
    width: 33.33%;
}
.stat-value {
    font-size: 24px;
    font-weight: bold;
    color: #1a73e8;
}
.stat-label {
    font-size: 12px;
    color: #5f6368;
}
</style>
"""


def latex_to_img(md_content: str) -> str:
    """Convert LaTeX formulas to image tags for email compatibility.

    Uses codecogs.com API to render LaTeX as SVG images (better quality).
    Supports both inline ($...$) and block ($$...$$) formulas.

    Args:
        md_content: Markdown content with LaTeX formulas.

    Returns:
        Markdown with LaTeX replaced by img tags.
    """
    import re
    import urllib.parse

    # Use SVG format for better quality
    # Note: Don't use \dpi{} - codecogs doesn't support it in URL params
    base_url = "https://latex.codecogs.com/svg.latex?"

    def make_img_tag(latex: str, is_block: bool = False) -> str:
        """Create an img tag for the LaTeX formula."""
        latex = latex.strip()
        # URL encode the LaTeX (no extra formatting - codecogs is picky)
        encoded = urllib.parse.quote(latex)
        url = f"{base_url}{encoded}"

        # Escape special chars for alt text
        alt_text = (
            latex.replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
        )

        if is_block:
            return f'\n\n<div style="text-align:center;margin:16px 0;"><img src="{url}" alt="{alt_text}" style="max-width:100%;"/></div>\n\n'
        else:
            return f'<img src="{url}" alt="{alt_text}" style="vertical-align:middle;height:1.1em;"/>'

    # Replace block formulas first ($$...$$)
    # Use non-greedy match
    def replace_block(match):
        latex = match.group(1)
        return make_img_tag(latex, is_block=True)

    # Replace inline formulas ($...$)
    def replace_inline(match):
        latex = match.group(1)
        # Skip if it looks like a price (e.g., $100)
        if latex.isdigit():
            return match.group(0)
        return make_img_tag(latex, is_block=False)

    # Block: $$...$$  (multiline supported, non-greedy)
    result = re.sub(r"\$\$(.+?)\$\$", replace_block, md_content, flags=re.DOTALL)

    # Inline: $...$  (single line, non-greedy, avoid matching $$)
    # Match $ followed by non-$ content, ending with $ not followed by $
    result = re.sub(r"(?<!\$)\$([^\$\n]+?)\$(?!\$)", replace_inline, result)

    return result


def render_markdown_to_html(md_content: str) -> str:
    """Convert markdown to HTML with syntax highlighting.

    Args:
        md_content: Markdown content string.

    Returns:
        HTML string.
    """
    # First, convert LaTeX formulas to images
    md_content = latex_to_img(md_content)

    # Configure markdown extensions
    extensions = [
        "fenced_code",
        "codehilite",
        "tables",
        "nl2br",
    ]

    extension_configs = {
        "codehilite": {
            "css_class": "highlight",
            "linenums": False,
        }
    }

    html = markdown.markdown(
        md_content, extensions=extensions, extension_configs=extension_configs
    )

    return html


def render_email_html(
    new_content: Optional[str] = None,
    new_topic: Optional[str] = None,
    new_category: Optional[str] = None,
    review_contents: Optional[list[str]] = None,
    stats: Optional[dict] = None,
) -> str:
    """Render the full email HTML.

    Args:
        new_content: Generated markdown content for new knowledge.
        new_topic: The topic name for new knowledge.
        new_category: The category for new knowledge.
        review_contents: List of review question markdown strings.
        stats: Statistics dictionary for progress display.

    Returns:
        Complete HTML email body.
    """
    today = date.today().strftime("%Y年%m月%d日")

    # Start building HTML
    html_parts = [
        f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    {EMAIL_STYLES}
</head>
<body>
<div class="container">
    <h1>🧠 每日 AI 知识卡片</h1>
    <p style="color: #5f6368;">📅 {today}</p>
"""
    ]

    # Progress stats
    if stats:
        html_parts.append(
            f"""
    <div class="stats">
        <div class="stat-item">
            <div class="stat-value">{stats.get('learned_topics', 0)}</div>
            <div class="stat-label">已学习</div>
        </div>
        <div class="stat-item">
            <div class="stat-value">{stats.get('unlearned_topics', 0)}</div>
            <div class="stat-label">待学习</div>
        </div>
        <div class="stat-item">
            <div class="stat-value">{stats.get('progress_percent', 0)}%</div>
            <div class="stat-label">进度</div>
        </div>
    </div>
"""
        )

    # New knowledge section
    if new_content and new_topic:
        category_info = CATEGORIES.get(new_category, {})
        emoji = category_info.get("emoji", "📚")

        html_parts.append(
            f"""
    <div class="new-section">
        <h2>🌟 今日新知</h2>
        <span class="category-badge category-{new_category}">{emoji} {new_category}</span>
        <h3>{new_topic}</h3>
        {render_markdown_to_html(new_content)}
    </div>
"""
        )

    # Review section
    if review_contents:
        html_parts.append(
            """
    <div class="review-section">
        <h2>🔄 今日复习</h2>
        <p>根据艾宾浩斯遗忘曲线，以下是今天需要复习的知识点：</p>
"""
        )
        for review_content in review_contents:
            html_parts.append(
                f"""
        <div style="margin: 20px 0; padding: 15px; background: white; border-radius: 8px;">
            {render_markdown_to_html(review_content)}
        </div>
"""
            )
        html_parts.append("    </div>")

    # No content case
    if not new_content and not review_contents:
        html_parts.append(
            """
    <div style="text-align: center; padding: 40px;">
        <p style="font-size: 48px;">🎉</p>
        <h2>今日无待学习内容</h2>
        <p>所有知识点已学习，或今日无复习安排。</p>
    </div>
"""
        )

    # Footer
    html_parts.append(
        """
    <div class="footer">
        <p>📚 DailyKnowledge - 每日 AI 知识推送系统</p>
        <p>基于艾宾浩斯遗忘曲线的间隔重复学习</p>
    </div>
</div>
</body>
</html>
"""
    )

    full_html = "".join(html_parts)

    # Use premailer to inline CSS for email compatibility
    # Suppress CSS warnings (premailer/cssutils complain about modern CSS properties)
    import logging
    import warnings

    # Suppress cssutils warnings
    cssutils_logger = logging.getLogger("cssutils")
    cssutils_level = cssutils_logger.level
    cssutils_logger.setLevel(logging.CRITICAL)

    # Suppress premailer warnings
    premailer_logger = logging.getLogger("premailer")
    premailer_level = premailer_logger.level
    premailer_logger.setLevel(logging.CRITICAL)

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = transform(full_html)
        return result
    except Exception:
        # Fallback if premailer fails
        return full_html
    finally:
        cssutils_logger.setLevel(cssutils_level)
        premailer_logger.setLevel(premailer_level)


def send_email(subject: str, html_body: str, text_body: Optional[str] = None) -> bool:
    """Send an email via SMTP.

    Args:
        subject: Email subject line.
        html_body: HTML content of the email.
        text_body: Plain text fallback (optional).

    Returns:
        True if email was sent successfully, False otherwise.

    Raises:
        ValueError: If SMTP credentials are not configured.
    """
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        raise ValueError("SMTP credentials are not configured")

    if not EMAIL_FROM or not EMAIL_TO:
        raise ValueError("Email addresses are not configured")

    # Create message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO

    # Add text part (fallback)
    if text_body:
        msg.attach(MIMEText(text_body, "plain", "utf-8"))

    # Add HTML part
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        # Handle multiple recipients
        recipients = [r.strip() for r in EMAIL_TO.split(",")]

        # Connect to SMTP server
        # Port 465 uses SSL, Port 587 uses STARTTLS
        if SMTP_PORT == 465:
            # SSL mode (常用于 QQ 邮箱)
            import ssl

            # Create SSL context with more permissive settings for compatibility
            context = ssl.create_default_context()
            # Disable hostname checking for some Chinese email providers
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            with smtplib.SMTP_SSL(
                SMTP_SERVER, SMTP_PORT, context=context, timeout=30
            ) as server:
                # 重要：先发送 EHLO 握手命令，避免 QQ 邮箱等服务器返回异常响应
                server.ehlo()
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                try:
                    server.sendmail(EMAIL_FROM, recipients, msg.as_string())
                except SMTPResponseException as e:
                    # QQ 邮箱等服务器会在成功发送后返回 (-1, b'\x00\x00\x00')
                    # 这实际上表示邮件已成功发送，只是响应码异常
                    print(
                        f"[DEBUG] SMTPResponseException caught: smtp_code={e.smtp_code}, smtp_error={e.smtp_error}"
                    )
                    if e.smtp_code == -1:
                        # 忽略这个"假错误"，邮件已经成功发送
                        print("[DEBUG] Ignoring -1 error code, email sent successfully")
                        pass
                    else:
                        # 其他真正的错误需要抛出
                        print(f"[DEBUG] Re-raising exception with code {e.smtp_code}")
                        raise
        else:
            # STARTTLS mode (常用于 Gmail)
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.sendmail(EMAIL_FROM, recipients, msg.as_string())

        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"SMTP authentication failed: {e}")
        print(
            "Please check your SMTP_USERNAME and SMTP_PASSWORD (use app-specific password)"
        )
        return False
    except smtplib.SMTPConnectError as e:
        print(f"SMTP connection failed: {e}")
        print(f"Please check SMTP_SERVER ({SMTP_SERVER}) and SMTP_PORT ({SMTP_PORT})")
        return False
    except SMTPResponseException as e:
        # 如果异常到这里，说明内层没有正确处理
        print(
            f"[DEBUG] SMTPResponseException reached outer handler: type={type(e)}, smtp_code={e.smtp_code}, smtp_error={e.smtp_error}"
        )
        # 对于 -1 错误码，认为发送成功
        if e.smtp_code == -1:
            print("[INFO] Email sent successfully (ignoring QQ mailbox response quirk)")
            return True
        else:
            print(f"Failed to send email: SMTP error code {e.smtp_code}")
            return False
    except Exception as e:
        print(f"[DEBUG] Unexpected exception type: {type(e)}")
        print(f"Failed to send email: {e}")
        return False


def send_daily_email(
    new_content: Optional[str] = None,
    new_topic: Optional[str] = None,
    new_category: Optional[str] = None,
    review_contents: Optional[list[str]] = None,
    stats: Optional[dict] = None,
) -> bool:
    """Send the daily knowledge email.

    Args:
        new_content: Generated markdown content for new knowledge.
        new_topic: The topic name for new knowledge.
        new_category: The category for new knowledge.
        review_contents: List of review question markdown strings.
        stats: Statistics dictionary for progress display.

    Returns:
        True if email was sent successfully, False otherwise.
    """
    today = date.today().strftime("%m/%d")

    # Build subject line
    subject_parts = [f"🧠 [{today}] 每日AI知识"]
    if new_topic:
        subject_parts.append(f"新知: {new_topic}")
    if review_contents:
        subject_parts.append(f"复习: {len(review_contents)}题")

    subject = " | ".join(subject_parts)

    # Render HTML
    html_body = render_email_html(
        new_content=new_content,
        new_topic=new_topic,
        new_category=new_category,
        review_contents=review_contents,
        stats=stats,
    )

    # Create plain text fallback
    text_parts = [f"每日AI知识 - {today}\n\n"]
    if new_topic:
        text_parts.append(f"今日新知: {new_topic}\n\n{new_content or ''}\n\n")
    if review_contents:
        text_parts.append("今日复习:\n\n" + "\n---\n".join(review_contents or []))
    text_body = "".join(text_parts)

    return send_email(subject, html_body, text_body)
