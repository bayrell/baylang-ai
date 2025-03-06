<?php

return function($loader)
{
	$plugins = __DIR__ . "/plugins";
	
	/* Init plugins */
	$loader->add("Runtime",  $plugins . "/Runtime/php");
	$loader->add("Runtime.Admin",  $plugins . "/Runtime.Admin/php");
	$loader->add("Runtime.Auth",  $plugins . "/Runtime.Auth/php");
	$loader->add("Runtime.Crypt",  $plugins . "/Runtime.Crypt/php");
	$loader->add("Runtime.ORM",  $plugins . "/Runtime.ORM/php");
	$loader->add("Runtime.Web",  $plugins . "/Runtime.Web/php");
	$loader->add("Runtime.Widget",  $plugins . "/Runtime.Widget/php");
	
	/* Init app */
	$loader->add("App",  __DIR__ . "/main/App/php");
	
	/* Init loader */
	$loader->init();
	
	/* Init modules */
	$loader->modules[] = "App";
	$loader->modules[] = "Runtime.ORM";
	$loader->modules[] = "Runtime.Web";
	$loader->modules[] = "Runtime.Widget";
	
	/* Setup environments */
	$loader->setEnv("LOCALE", "en");
	$loader->setEnv("TZ", "Asia/Almaty");
	$loader->setEnv("TZ_OFFSET", 5);
	if (isset($_SERVER["HTTP_X_FORWARDED_PREFIX"]))
		$loader->setEnv("ROUTE_PREFIX", $_SERVER["HTTP_X_FORWARDED_PREFIX"]);
	
	/* Read environments */
	$loader->include(__DIR__ . "/env.php");
};