# Read the current dashboard file
with open('templates/dashboard.html', 'r') as f:
    content = f.read()

# Find the navigation section and add voice link
old_nav = '''            <a href="/schedule" style="margin: 0 15px; color: #007bff;">? Schedule</a>
            <a href="/settings" style="margin: 0 15px; color: #007bff;">?? Settings</a>
            <a href="javascript:location.reload()" style="margin: 0 15px; color: #007bff;">? Refresh</a>'''

new_nav = '''            <a href="/schedule" style="margin: 0 15px; color: #007bff;">? Schedule</a>
            <a href="/settings" style="margin: 0 15px; color: #007bff;">?? Settings</a>
            <a href="/voice" style="margin: 0 15px; color: #007bff;">? Voice Calls</a>
            <a href="javascript:location.reload()" style="margin: 0 15px; color: #007bff;">? Refresh</a>'''

# Replace the navigation
new_content = content.replace(old_nav, new_nav)

# Write back to file
with open('templates/dashboard.html', 'w') as f:
    f.write(new_content)

print("Voice Calls link added to dashboard!")
