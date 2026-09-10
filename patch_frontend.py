from pathlib import Path

p = Path('/app/app/static/index.html')
s = p.read_text()

s = s.replace(
    '<input id="email" type="email" placeholder="Email"><input id="password" type="password" placeholder="Password (8+ characters)">',
    '<input id="email" type="email" inputmode="email" autocomplete="email" required placeholder="Email"><input id="password" type="password" autocomplete="current-password" minlength="8" required placeholder="Password (8+ characters)">'
)

old_login = 'async function login(){try{let x=await A("/api/auth/login",{method:"POST",body:JSON.stringify({email:$("email").value,password:$("password").value})});localStorage.tf_token=T=x.access_token;boot()}catch(e){$("authmsg").textContent=e.message}}'
new_login = '''async function login(){let email=$("email").value.trim(),password=$("password").value;if(!email||!email.includes("@")){ $("authmsg").textContent="Enter your email address first.";return }if(password.length<8){$("authmsg").textContent="Password must be at least 8 characters.";return}try{let x=await A("/api/auth/login",{method:"POST",body:JSON.stringify({email,password})});localStorage.tf_token=T=x.access_token;boot()}catch(e){$("authmsg").textContent="Login failed. Check your email and password."}}'''

old_register = 'async function register(){try{let x=await A("/api/auth/register",{method:"POST",body:JSON.stringify({email:$("email").value,password:$("password").value,name:""})});localStorage.tf_token=T=x.access_token;boot()}catch(e){$("authmsg").textContent=e.message}}'
new_register = '''async function register(){let email=$("email").value.trim(),password=$("password").value;if(!email||!email.includes("@")){ $("authmsg").textContent="Enter a valid email address first.";return }if(password.length<8){$("authmsg").textContent="Create a password with at least 8 characters.";return}$("authmsg").textContent="Creating account…";try{let x=await A("/api/auth/register",{method:"POST",body:JSON.stringify({email,password,name:""})});localStorage.tf_token=T=x.access_token;boot()}catch(e){let msg=e.message;try{let j=JSON.parse(msg);msg=j.detail||msg}catch{}$("authmsg").textContent=typeof msg==="string"?msg:"Could not create account. Try a different email."}}'''

if old_login not in s or old_register not in s:
    raise SystemExit('Expected auth functions not found; refusing to patch')
s = s.replace(old_login, new_login).replace(old_register, new_register)
p.write_text(s)
print('ThemeForge auth form patched')
