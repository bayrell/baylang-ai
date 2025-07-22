import ChatPageModel from "./Chat/ChatPageModel.js";
import Router from "./Router.js";

class Layout
{
	constructor()
	{
		this.router = new Router(this);
		this.chat_page = new ChatPageModel(this);
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