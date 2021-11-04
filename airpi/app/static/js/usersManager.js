// On load renders users
window.onload = async function(){
    getDBUsers().then(d => {
        renderToScreen(d)
    })
}

// Requests all users
async function getDBUsers(){
    let res = await fetch('/api/users', {
        method: 'GET',
        cache: 'no-cache',
        header: {
            'Content-Tye': 'application/json'
        }
    });

    return await res.json();
}

// Updates user information
async function updateUser(data){
    let res = await fetch('/api/users',{
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRF-TOKEN': getCookie('csrf_access_token'),
        },
        credentials: 'same-origin',
        body: JSON.stringify(data)
    })

    return await res.json();
}

// Creates a new user
async function newUser(data){
    let res = await fetch('/api/users', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRF-TOKEN': getCookie('csrf_access_token'),
        },
        credentials: 'same-origin',
        body: JSON.stringify(data)
    })
    return await res.json();
}

// Deletes the requested user
async function delUser(data){
    let res = await fetch('/api/users', {
        method: 'DELETE',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRF-TOKEN': getCookie('csrf_access_token'),
        },
        credentials: 'same-origin',
        body: JSON.stringify(data)
    })
    return await res.json();
}

// Handles the user update form submission
$("#userUpdate").submit(function(e){
    e.preventDefault();
    let form = $(this).serializeJSON();

    if(form.newpass1 != form.newpass2){
        alert("Password don't match!")
        return;
    }

    if (form.newpass1 != form.newpass2){
        alert("Password don't match!");
        return;
    }

    data = {
        username: form.username,
        reqPassword: form.reqpass,
        newAdmin: form.useradmin === "on"
    }

    if (form.updatepass === "on"){
        data.newPassword = form.newpass1;
    }


    updateUser(data)
    .then(res => {
        getDBUsers().then(d => renderToScreen(d));
        $("#edit").modal('hide');
    })
    .catch(err => {
        console.log(err);
        alert("An error happend. Make sure to specifiy your password.");
    })
});

// Handles the new user form submission
$("#newUser").submit(function(e){
  e.preventDefault();
  let form = $(this).serializeJSON();

  if (form.usernewpass1 != form.usernewpass2){
      alert("Password don't match!")
      return;
  }

  data = {
    username: form.newusername,
    newPassword: form.usernewpass1,
    reqPassword: form.newreqpass,
    newAdmin: form.usernewadmin === 'on'
  }

  newUser(data)
  .then(res => {
      getDBUsers().then(d => renderToScreen(d));
      $("#new").modal('hide');
  })
  .catch(res => {
      alert("An error happend");
  })

});

// Renders the table to screen using the provided skeleton
function renderToScreen(res){
  $("tbody").html("");
  let index = 1;
  res.forEach(element => {
    if (element.is_admin){
        element.is_admin = "Yes";
    }else{
        element.is_admin = "No";
    }

    let table = document.getElementById("usersTable")
    let row = table.insertRow(0);
    row.setAttribute('data-username', element.username);

    let cell1 = row.insertCell(0);
    cell1.classList.add('align-middle');
    cell1.setAttribute('class', 'align-middle');
    cell1.setAttribute('scope', 'row');
    cell1.innerHTML = index;

    let cell2 = row.insertCell(1);
    cell2.setAttribute('class', 'align-middle');
    cell2.setAttribute('scope', 'row');
    cell2.innerHTML = element.username;

    let cell3 = row.insertCell(2);
    cell3.setAttribute('class', 'align-middle');
    cell3.innerHTML = element.is_admin

    let cell4 = row.insertCell(3);
    cell4.innerHTML = '<button type="button" class="btn btn-secondary usersettings"><i class="bi bi-gear-wide"></i></button>';

    let cell5 = row.insertCell(4);
    cell5.innerHTML = '<button type="button" class="btn btn-danger deleter"><i class="bi bi-trash"></i></button>';


    index++;


  });

    // Shows modal menu for users settings
    $(".usersettings").on('click', (e) => {
        $("#edit").modal('show');
        let username = $(e.target).closest("tr").data('username');
        $("#edituser").val(username);
    })

    // Handles the user delete event
    $(".deleter").on('click', (e) => {
        let username = $(e.target).closest("tr").data('username');

        delUser({username: username})
            .then(res => {
                getDBUsers().then(d => renderToScreen(d));
            })
            .catch(err => {
                alert("Coudln't delete the user")
            })
    })
}