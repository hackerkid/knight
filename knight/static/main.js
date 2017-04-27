function onSignIn(googleUser) {
  var profile = googleUser.getBasicProfile();
  var user_details = {
      "email": profile.getEmail(),
      "token": googleUser.getAuthResponse().id_token,
      "auth": "google"
  }
  $.ajax({
    type: "POST",
    url: "/login",
    data: user_details,
    success: function(data) {
      window.location.replace("/")
    }
  });
}

function signOut() {
  onLoad();
  var auth2 = gapi.auth2.getAuthInstance();
  auth2.signOut().then(function () {
    console.log('User signed out.');
  });
  window.location.replace("/logout")
}

 function onLoad() {
  gapi.load('auth2', function() {
    gapi.auth2.init();
  });
}

function getParameterByName(name, url) {
    if (!url) url = window.location.href;
    name = name.replace(/[\[\]]/g, "\\$&");
    var regex = new RegExp("[?&]" + name + "(=([^&#]*)|&|#|$)"),
        results = regex.exec(url);
    if (!results) return null;
    if (!results[2]) return '';
    return decodeURIComponent(results[2].replace(/\+/g, " "));
}


  $.ajax({
    type: "POST",
    url: "/api/article/info",
    data: {"url": getParameterByName("url")},
    success: function(data) {
        console.log(getParameterByName("url"));
        $('#article-title').text(data.title);
        $("#article-image").attr("src", data.image);
    }
  });

