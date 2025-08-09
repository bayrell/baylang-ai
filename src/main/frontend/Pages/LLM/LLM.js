import { sendApi } from "@main/lib.js"
import FormModel from "@main/Components/Form/FormModel.js";

class LLM
{
	/**
	 * Constructor
	 */
	constructor(layout)
	{
		this.layout = layout;
		this.items = [];
		this.form = new FormModel();
	}
	
	
	/**
	 * Init
	 */
	init()
	{
	}
	
	
	/**
	 * Find item by id
	 */
	findItemById(id)
	{
		return this.items.find((item) => item.id == id);
	}
	
	
	/**
	 * Load data
	 */
	async load()
	{
		this.items = [];
		var result = await sendApi(
			"/api/settings/llm",
		);
		if (result.isSuccess())
		{
			this.items = result.data.items;
		}
	}
	
	
	/**
	 * Save item
	 */
	async save(pk, item)
	{
		var result = await sendApi(
			"/api/settings/llm/save",
			{
				"id": pk ? pk.id : null,
				"item": item,
			}
		);
		return result;
	}
	
	
	/**
	 * Delete item
	 */
	async delete(id)
	{
		var result = await sendApi(
			"/api/settings/llm/delete",
			{
				"id": id,
			}
		);
		
		if (result.isSuccess())
		{
			var index = this.items.find((item) => item.id == id);
			this.items.slice(index, 1);
		}
		return result;
	}
	
	
	/**
	 * Reload models
	 */
	async reloadModels()
	{
		var result = await sendApi(
			"/api/settings/llm/get_models",
			{
				"id": this.form.item.id,
				"item": this.form.item,
			}
		);
		
		if (result.isSuccess())
		{
			this.form.item.content.models = result.data.items;
		}
		return result;
	}
}

export default LLM;