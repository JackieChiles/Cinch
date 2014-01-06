// Template for untracked server config file.

if (document.location.origin == "http://localhost") {
    // Local server enabled for testing
    var host_path = "http://localhost:8088/cinch";
}
else {
    // Customize the following line to match the external server.
    var host_path = "http://www.example.com:65000/cinch";
}

var host_path = "http://localhost:8088/cinch";
