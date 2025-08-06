import ChatPageModel from "./Chat/ChatPageModel.js";
import Router from "./Router.js";
import LLM from "./Settings/LLM.js";

class Layout
{
	constructor()
	{
		this.router = new Router(this);
		this.chat_page = new ChatPageModel(this);
		this.llm = new LLM(this);
	}
	
	
	/**
	 * Init layout
	 */
	init()
	{
		this.router.init();
		this.chat_page.init();
		this.llm.init();
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