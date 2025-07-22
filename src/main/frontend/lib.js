export function apply(object, method_name, args)
{
	var method = object[method_name].bind(object);
	return method.apply(null, args);
}
export function callback(object, method){
	return (...args) =>
	{
		return apply(object, method, args);
	}
}


export class ApiResult
{
	code = 0;
	message = "";
	data = {};
	response = null;
	
	
	/**
	 * Assign response
	 */
	assign(response)
	{
		this.response = response;
		this.code = response.code;
		this.message = response.message;
		this.data = response.data;
	}
	
	
	/**
	 * Returns true if error
	 */
	isError()
	{
		return this.code < 0;
	}
	
	
	/**
	 * Returns true if success
	 */
	isSuccess()
	{
		return this.code > 0;
	}
	
	
	/**
	 * Returns data
	 */
	getData()
	{
		return this.data;
	}
}


/**
 * Build URLSearchParams key
 */
export function buildURLSearchParamsKey(path)
{
	if (path.length == 0) return "";
	if (path.length == 1) return path[0];
	var name = path[0];
	path = path.slice(1);
	return name + "[" + path.join("][") + "]";
}


/**
 * Update URLSearchParams
 */
export function updateURLSearchParams(post, path, params)
{
	if (Array.isArray(post))
	{
		for (var i=0; i<post.length; i++)
		{
			updateURLSearchParams(post[i], path.concat(i), params);
		}
	}
	else if (typeof post == "object" && !(post instanceof File))
	{
		for (var key in post)
		{
			updateURLSearchParams(post[key], path.concat(key), params);
		}
	}
	else
	{
		var key = buildURLSearchParamsKey(path);
		params.append(key, post);
	}
}


/**
 * Returns URLSearchParams
 */
export function getURLSearchParams(post)
{
	var params = new URLSearchParams();
	updateURLSearchParams(post, [], params);
	return params;
}


/**
 * Send api
 */
export async function sendApi(url, post)
{
	if (post == undefined) post = {};
	var response = await fetch(url, {
		method: "POST",
		headers: {
			"Content-Type": "application/x-www-form-urlencoded",
		},
		body: getURLSearchParams(post),
	});
	var result = new ApiResult();
	if (response.status == 200)
	{
		var data = await response.json();
		result.assign(data);
	}
	else
	{
		result.code = -1;
		result.message = "Error " + response.status;
	}
	return result;
}