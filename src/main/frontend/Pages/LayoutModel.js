import Router from "./Router.js";

class Layout
{
	constructor()
	{
		this.router = new Router(this);
	}
	
	
	/**
	 * Init layout
	 */
	init()
	{
		this.router.init();
	}
	
	
	/**
	 * Load data
	 */
	async load()
	{
	}
	
	
	/**
	 * Repaint
	 */
	repaint()
	{
	}
}

export default Layout;