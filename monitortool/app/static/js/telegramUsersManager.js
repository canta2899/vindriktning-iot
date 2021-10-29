
window.onload = getUsers();

async function getUsers(){
    $.ajax({
      method: 'GET', 
      url: '/api/telegram',
      cache: 'no-cache',
      headers: {
        'Content-Type': 'application/json'
      },
      dataType: "json",
      success: function(data){
        renderToScreen(data.users)
      },
      error: function(){
        alert("An error occoured");
      }
    })
}

$("#newTokenForm").submit(e => {
    e.preventDefault();
    var form = document.querySelector("#newTokenForm");
    var username = form.querySelector('input[name="username"]').value;

    var msg = {
        username: username,
    };

    $.ajax({
      method: 'POST',
      url: '/api/telegram',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRF-TOKEN': getCookie('csrf_access_token')
      },
      credentials: 'same-origin',
      data: JSON.stringify({username: username}),
      success: function(){
        getUsers();
        $("#add").modal('hide');
      },
      error: function(){
        alert("Unable to add new user");
      }
    })
});

function renderToScreen(res){
  $("tbody").html("");
  let index = 1;
  res.forEach(element => {
      if (element.chat_id == null){
          element.chat_id = "Unknown";
      }
      $("tbody").append("<tr data-username='" + element.username + "'><td class='align-middle' scope='row'>" + index + "</td><td class='align-middle username'>"+element.username+"</td><td class='align-middle'>"+element.chat_id + "</td><td><button type='button' class='btn btn-danger deleter' onclick='deleteUser();'><i class='bi bi-trash'></i></button></td></tr>");
      
      let table = document.getElementById("tbody")
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

function deleteUser(){
  let username = $('.deleter').closest("tr").data('username');
    $.ajax({
        url: '/api/telegram',
        method: 'DELETE', 
        headers: {
            'Content-Type': 'application/json',
            'X-CSRF-TOKEN': getCookie('csrf_access_token'),
        },        
        credentials: 'same-origin',
        data: JSON.stringify({username: username}),
        success: function(){
          getUsers();
        },
        error: function(){
          alert("There's no user with that name");
        }
    });
}