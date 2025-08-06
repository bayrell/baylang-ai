import ResultModel from "./ResultModel.js";

class FormModel
{
	constructor()
	{
		this.pk = null;
		this.item = {};
		this.errors = {};
		this.result = new ResultModel();
	}
	
	
	/**
	 * Clear form
	 */
	clear()
	{
		this.pk = null;
		this.item = {};
		this.errors = {};
		this.result.clear();
	}
	
	
	/**
	 * Set primary key
	 */
	setPrimaryKey(pk)
	{
		this.pk = pk;
	}
	
	
	/**
	 * Set item
	 */
	setItem(item)
	{
		this.item = Object.assign({}, item);
	}
	
	
	/**
	 * Set api result
	 */
	setApiResult(api_result)
	{
		this.result.setApiResult(api_result);
		if (api_result.code < 0 && api_result.response && api_result.response.fields != undefined)
		{
			this.errors = api_result.response.fields;
		}
	}
	
	
	/**
	 * Returns field error
	 */
	getFieldError(key)
	{
		return this.errors[key] || "";
	}
}

export default FormModel;