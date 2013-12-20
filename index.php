<?php

exec("ps aux | grep -i 'cinch' | grep -v grep", $pids);

if (empty($pids)) {
    header("Cache-Control: no-cache, must-revalidate"); // HTTP/1.1
    header("Expires: Sat, 26 Jul 1997 05:00:00 GMT"); // Date in the past
    header( 'HTTP/1.1 418 I\'m a teapot' );
    header( 'Location: ./offline.html' );
    exit;
} else {
    // Provide redirection to home.html
    header("Cache-Control: no-cache, must-revalidate"); // HTTP/1.1
    header("Expires: Sat, 26 Jul 1997 05:00:00 GMT"); // Date in the past
    header( 'HTTP/1.1 302 Moved ' );
    header( 'Location: ./home.html' );
}
?>
