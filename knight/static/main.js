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

