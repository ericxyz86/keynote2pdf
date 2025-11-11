# Security Fixes Applied

This document summarizes the security vulnerabilities that were identified and fixed in the Keynote2PDF application.

## Date: 2025-11-11

---

## 1. CRITICAL: AppleScript Injection Vulnerability ✅ FIXED

**Location**: `app.py:217-265` (keynote_to_pdf function)

**Vulnerability**: File paths were directly interpolated into AppleScript without proper escaping, allowing potential code injection.

**Fix Applied**:
- Added `escape_applescript_string()` function that properly escapes backslashes and double quotes
- Updated `keynote_to_pdf()` to escape both `key_filepath` and `pdf_filepath` before inserting into AppleScript
- Prevents attackers from breaking out of string context and executing arbitrary AppleScript commands

**Code Changes**:
```python
def escape_applescript_string(s):
    """Escapes a string for safe inclusion in AppleScript."""
    if s is None:
        return ""
    s = s.replace("\\", "\\\\")
    s = s.replace('"', '\\"')
    return s
```

---

## 2. CRITICAL: Insecure Default Secret Key ✅ FIXED

**Location**: `app.py:37-47`

**Vulnerability**: Hardcoded default secret key `"your_very_secret_key_here"` was publicly visible and predictable.

**Fix Applied**:
- Added `secrets` module import for cryptographically secure random generation
- Removed hardcoded default secret key
- Now generates a secure random key using `secrets.token_hex(32)` if `FLASK_SECRET_KEY` environment variable is not set
- Added warning log message when auto-generating key
- Prevents session hijacking and CSRF bypass attacks

**Code Changes**:
```python
secret_key = os.environ.get("FLASK_SECRET_KEY")
if not secret_key:
    secret_key = secrets.token_hex(32)
    logging.warning(
        "FLASK_SECRET_KEY not set. Generated temporary key. "
        "Set FLASK_SECRET_KEY environment variable for production use."
    )
app.secret_key = secret_key
```

---

## 3. HIGH: Information Disclosure via Error Messages ✅ FIXED

**Location**: Multiple locations (upload, merge, delete endpoints)

**Vulnerability**: Detailed exception messages and stack traces were exposed to users, revealing internal paths and system information.

**Fix Applied**:
- Created `log_error_return_generic()` helper function
- Logs detailed errors server-side with full stack trace
- Returns generic error message to users: "An error occurred while processing your request. Please try again."
- Updated error handling in:
  - File upload handler (`app.py:642-646`)
  - Merge endpoint (`app.py:794-796`)
  - Delete endpoint (`app.py:820-822`)

**Code Changes**:
```python
def log_error_return_generic(error, context=""):
    """Logs detailed error information server-side and returns generic message."""
    logging.error(f"{context}: {error}", exc_info=True)
    return "An error occurred while processing your request. Please try again."
```

---

## 4. MEDIUM: Missing Security Headers ✅ FIXED

**Location**: `app.py:560-581`

**Vulnerability**: No security headers were configured, leaving the application vulnerable to various web attacks.

**Fix Applied**:
Added `@app.after_request` handler to include comprehensive security headers:
- **X-Frame-Options: DENY** - Prevents clickjacking attacks
- **X-Content-Type-Options: nosniff** - Prevents MIME-type sniffing
- **X-XSS-Protection: 1; mode=block** - Enables XSS filter
- **Content-Security-Policy** - Restricts resource loading to trusted sources
  - `default-src 'self'` - Only allow same-origin by default
  - `style-src 'self' 'unsafe-inline' https://fonts.googleapis.com` - Allow inline styles and Google Fonts
  - `font-src 'self' https://fonts.gstatic.com` - Allow Google Fonts
  - `script-src 'self' 'unsafe-inline'` - Allow inline scripts (required for current template)
  - `img-src 'self' data:` - Allow same-origin and data URIs for images
- **Strict-Transport-Security** (production only) - Forces HTTPS connections

---

## 5. MEDIUM: Potential DoS via Decompression Bomb ✅ FIXED

**Location**: `app.py:23-25`

**Vulnerability**: `Image.MAX_IMAGE_PIXELS = None` disabled all decompression bomb protection, allowing malicious images to consume excessive memory.

**Fix Applied**:
- Set reasonable limit: `Image.MAX_IMAGE_PIXELS = 500_000_000` (500 million pixels)
- This allows images up to approximately 22,000 x 22,000 pixels
- Sufficient for legitimate presentations while protecting against DoS attacks
- Added explanatory comment documenting the limit

---

## 6. LOW: Unused Code with Security Risk ✅ FIXED

**Location**: Removed from codebase

**Vulnerability**: Two unused functions posed potential security risks if ever activated:
1. `convert_to_pdfa()` - Used Ghostscript with potential command injection risk
2. `compress_pdf()` - Dead code that added maintenance burden

**Fix Applied**:
- Completely removed `convert_to_pdfa()` function (app.py:90-123)
- Completely removed `compress_pdf()` function (app.py:295-349)
- Reduces attack surface and code complexity
- Eliminates potential for accidental activation of risky code

---

## Remaining Considerations (Already Mitigated)

### Path Traversal Protection ✅ ALREADY SECURE
- `secure_filename()` used consistently on all user input
- `send_from_directory()` provides built-in path traversal protection
- `os.path.join()` prevents `../` attacks

### XSS Protection ✅ ALREADY SECURE
- Flask's Jinja2 auto-escaping enabled by default
- No unsafe filters (`|safe`, `|raw`) used in templates
- User input is automatically escaped in HTML context

### CSRF Protection ⚠️ LOW RISK
- Application binds to localhost (127.0.0.1) in production
- POST endpoints (`/merge`, `/delete`) accept JSON without CSRF tokens
- Risk is minimal since external attackers cannot access localhost
- If application is ever exposed beyond localhost, CSRF protection should be added

---

## Testing Recommendations

1. **Test secret key generation**:
   - Verify warning appears when `FLASK_SECRET_KEY` is not set
   - Confirm sessions work correctly with generated key

2. **Test AppleScript escaping**:
   - Test with filenames containing quotes: `test"file.key`
   - Test with filenames containing backslashes: `test\file.key`

3. **Test error handling**:
   - Verify detailed errors appear in logs but not in user responses
   - Confirm generic error messages are shown to users

4. **Test security headers**:
   - Use browser developer tools or `curl -I` to verify headers are present
   - Test CSP doesn't break page functionality

5. **Test image decompression limit**:
   - Verify normal presentations process successfully
   - Test with large images to ensure limit is reasonable

---

## Production Deployment Checklist

- [ ] Set `FLASK_SECRET_KEY` environment variable to a secure random value
- [ ] Ensure application binds only to localhost (127.0.0.1) or use reverse proxy
- [ ] Monitor logs for security warnings
- [ ] Consider adding rate limiting for additional DoS protection
- [ ] Regularly update dependencies (Flask, PyMuPDF, Pillow)
- [ ] Review logs periodically for suspicious activity

---

## References

- OWASP Top 10: https://owasp.org/www-project-top-ten/
- Flask Security Best Practices: https://flask.palletsprojects.com/en/latest/security/
- Content Security Policy: https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP
