import IndexPage from "./Index/IndexPage.vue";
import ChatPage from "./Chat/ChatPage.vue";
import NotFoundPage from "./NotFound/NotFoundPage.vue";
import { markRaw } from "vue";
import { callback } from "../lib.js";

class Router
{
	constructor(layout)
	{
		this.layout = layout;
		this.currentRoute = null;
		this.routes = [];
		this.registerRoutes();
	}
	
	
	/**
	 * Init
	 */
	init()
	{
		window.addEventListener("popstate", callback(this, "updateRoute"));
		window.addEventListener("hashchange", callback(this, "updateRoute"));
		this.updateRoute();
	}
	
	
	/**
	 * Add route
	 */
	addRoute(path, component, title)
	{
		this.routes.push({
			path: path,
			title: title,
			component: markRaw(component),
		});
	}
	
	
	/**
	 * Register routes
	 */
	registerRoutes()
	{
		this.addRoute("/", IndexPage, "Main page");
		this.addRoute("/chat", ChatPage, "Chat page");
	}
	
	
	/**
	 * Get route path
	 */
	getRoute(path)
	{
		return this.routes.find(route => route.path === path);
	}
	
	
	/**
	 * Find route
	 */
	findRoute(path)
	{
		let route = this.getRoute(path);
		if (!route)
		{
			route =
			{
				path: path,
				component: markRaw(NotFoundPage),
				title: "Page not found"
			}
		}
		return route;
	}
	
	
	/**
	 * Update route
	 */
	updateRoute()
	{
		const route = this.findRoute(window.location.pathname);
		document.title = route.title;
		this.currentRoute = route;
		this.layout.repaint();
	}
	
	
	/**
	 * Push
	 */
	push(path)
	{
		window.history.pushState({}, "", path);
		this.updateRoute();
	}
	
	
	/**
	 * Pop
	 */
	pop()
	{
		window.history.back();
		this.updateRoute();
	}
}

export default Router;