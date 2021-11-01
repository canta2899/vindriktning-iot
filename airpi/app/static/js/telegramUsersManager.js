
// renders user table on load
window.onload = async function(){
  getUsers().then(d => {
    renderToScreen(d);
  });
};

// gets users asynchronously
async function getUsers(){
  let res = await fetch('/api/telegram', {
      method: 'GET',
      cache: 'no-cache',
      header: {
          'Content-Tye': 'application/json'
      }
  });

  return await res.json();
}

// creates a new user
async function newUser(data){
  let res = await fetch('/api/telegram', {
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

// deletes the requested user
async function delUser(data){
  let res = await fetch('/api/telegram', {
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

// Handles the submit event when adding user
$("#newTokenForm").submit(e => {
    e.preventDefault();
    var form = document.querySelector("#newTokenForm");
    var username = form.querySelector('input[name="username"]').value;

    var msg = {
        username: username,
    };

    newUser(msg)
      .then(res => {
        getUsers().then(res => renderToScreen(res));
      })
      .catch(err => alert("An error happened"))
});

// Creates the table using the provided skeleton
function renderToScreen(res){
  $("tbody").html("");
  let index = 1;
  console.log(res);
  res.forEach(element => {
      if (element.chat_id == null){
          element.chat_id = "Unknown";
      }
      
      let table = document.getElementById("tgtable")
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
      cell3.innerHTML = element.chat_id
  
      let cell4 = row.insertCell(3);
      cell4.innerHTML = "<button type='button' class='btn btn-danger deleter' onclick='deleteUser();'><i class='bi bi-trash'></i></button>";
  
      index++;
      
  });
}

// Handles the user deletion
function deleteUser(){
  let username = $('.deleter').closest("tr").data('username');
  let msg = {
    username: username
  }

  delUser(msg)
    .then(res => {
      getUsers().then(d => renderToScreen(d));
    })
    .catch(err => alert("An error happened"))
}