# Read the current voice.html template
with open('templates/voice.html', 'r') as f:
    content = f.read()

# Find where to add email section (after the message input)
old_section = '''            <div class="form-group">
                <label for="message">Voice Message (Maximum 60 characters)</label>
                <textarea id="message" 
                          name="message" 
                          maxlength="60" 
                          oninput="updateCharCounter()"
                          placeholder="Enter the message to be spoken during voice calls">{{ voice_config.message }}</textarea>
                <div class="char-counter" id="char-counter">0/60 characters</div>
            </div>

            <button type="submit" class="submit-btn">Save Voice Call Settings</button>'''

new_section = '''            <div class="form-group">
                <label for="message">Voice Message (Maximum 60 characters)</label>
                <textarea id="message" 
                          name="message" 
                          maxlength="60" 
                          oninput="updateCharCounter()"
                          placeholder="Enter the message to be spoken during voice calls">{{ voice_config.message }}</textarea>
                <div class="char-counter" id="char-counter">0/60 characters</div>
            </div>

            <div class="form-group">
                <label>Additional Email Notifications (optional)</label>
                <input type="email" 
                       name="email1" 
                       value="{{ voice_config.email1 or '' }}"
                       placeholder="Additional Email 1 (optional)"
                       style="margin-bottom: 10px;">
                <input type="email" 
                       name="email2" 
                       value="{{ voice_config.email2 or '' }}"
                       placeholder="Additional Email 2 (optional)"
                       style="margin-bottom: 10px;">
                <input type="email" 
                       name="email3" 
                       value="{{ voice_config.email3 or '' }}"
                       placeholder="Additional Email 3 (optional)">
                <div class="help-text" style="margin-top: 5px;">
                    These emails will receive alerts in addition to your main email address
                </div>
            </div>

            <button type="submit" class="submit-btn">Save Voice Call Settings</button>'''

# Replace the section
new_content = content.replace(old_section, new_section)

# Write back to file
with open('templates/voice.html', 'w') as f:
    f.write(new_content)

print("Email input fields added to voice template!")
