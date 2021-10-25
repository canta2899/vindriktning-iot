function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
}

async function auth(){
    const options = {
        method: 'post',
        credentials: 'same-origin',
        headers: {
        'X-CSRF-TOKEN': getCookie('csrf_access_token'),
        },
    };
    var auth = await fetch('/auth', options);
    return auth;
}
