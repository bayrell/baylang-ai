<?php

define('BASE_PATH', dirname(__DIR__));
ini_set('display_errors', 'on');
ini_set('html_errors', 'on');
set_time_limit(30);
require_once BASE_PATH . "/plugins/Runtime/bay/Loader.php";

/* Create loader */
$loader = new Loader();
$loader->include( BASE_PATH . "/init.php" );

/* Run web app */
$loader->entry_point = "Runtime.Web.BaseApp";
$loader->runApp();