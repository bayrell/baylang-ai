import ChatHistory from "./ChatHistory.js";
import ChatMessage from "./ChatMessage.js";
import { sendApi } from "@main/lib.js";
import { markRaw } from "vue";

class Socket
{
	constructor()
	{
		this.model = null;
		this.ws = null;
	}
	
	
	/**
	 * Set model
	 */
	setModel(model)
	{
		this.model = model;
	}
	
	
	/**
	 * Connect
	 */
	connect()
	{
		this.ws = new WebSocket("/api/chat/socket");
		this.ws.binaryType = 'arraybuffer';
		this.ws.onopen = this.onConnect.bind(this);
		this.ws.onmessage = this.onMessage.bind(this);
		this.ws.onclose = this.onDisconnect.bind(this);
		this.ws.onerror = this.onError.bind(this);
	}
	
	
	/**
	 * On connect
	 */
	onConnect()
	{
		console.log("Connected to websocket");
	}
	
	
	/**
	 * On disconnect
	 */
	onDisconnect()
	{
		console.log("Disconnected from websocket");
	}
	
	
	/**
	 * On message
	 */
	onMessage(message)
	{
		/* JSON decode */
		var item = null;
		try
		{
			item = JSON.parse(message.data);
		}
		catch(e)
		{
		}
		
		if (!item) return;
		if (item.event == "update_chat")
		{
			var chat_id = item.message.chat_id;
			var chat = this.model.findChatById(chat_id);
			if (!chat) return;
			
			/* Update message */
			chat.updateMessage(item.message);
			
			/* Set typing */
			var message = chat.lastMessage();
			if (message == null) chat.setTyping(true);
			else
			{
				var line = message.lastLine();
				if (line == null) chat.setTyping(true);
				else if (line.content == "") chat.setTyping(true);
				else chat.setTyping(false);
			}
		}
		else if (item.event == "start_chat")
		{
			var chat_id = item.message.chat_id;
			var chat = this.model.findChatById(chat_id);
			if (!chat) return;
			
			chat.setTyping(true);
		}
		else if (item.event == "end_chat")
		{
			var chat_id = item.message.chat_id;
			var chat = this.model.findChatById(chat_id);
			if (!chat) return;
			
			chat.setTyping(false);
		}
		else
		{
			console.log(item);
		}
	}
	
	
	/**
	 * On error
	 */
	onError()
	{
	}
}

class ChatPageModel
{
	/**
	 * Constructor
	 */
	constructor()
	{
		this.chats = [];
		this.socket = markRaw(new Socket());
		this.current_chat_id = null;
		this.is_loading = true;
		this.image_url = "";
		this.show_dialog = "";
		this.show_dialog_id = "";
		this.loading = true;
	}
	
	
	/**
	 * Init model
	 */
	init()
	{
		this.socket.setModel(this);
		this.socket.connect();
	}
	
	
	/**
	 * Find chat by id
	 */
	findChatById(id)
	{
		for (var i = 0; i<this.chats.length; i++)
		{
			var chat = this.chats[i];
			if (chat.id == id)
			{
				return chat;
			}
		}
		return null;
	}
	
	
	/**
	 * Find chat index by id
	 */
	findChat(id)
	{
		for (var i = 0; i<this.chats.length; i++)
		{
			var chat = this.chats[i];
			if (chat.id == id)
			{
				return i;
			}
		}
		return -1;
	}
	
	
	/**
	 * Select chat
	 */
	selectChat(pos)
	{
		if (pos < 0) pos = 0;
		if (pos >= this.chats.length) pos = this.chats.length - 1;
		if (this.chats.length == 0)
		{
			this.current_chat_id = "";
			return;
		}
		
		var chat = this.chats[pos];
		this.current_chat_id = chat.id;
	}
	
	
	/**
	 * Select item
	 */
	selectItem(id)
	{
		this.current_chat_id = id;
	}
	
	
	/**
	 * Returns current item
	 */
	getCurrentItem()
	{
		return this.findChatById(this.current_chat_id);
	}
	
	
	/**
	 * Returns current chat id
	 */
	getCurrentChatId()
	{
		var chat = this.findChatById(this.current_chat_id);
		if (!chat) return "";
		return this.current_chat_id;
	}
	
	
	/**
	 * Set image url
	 */
	setImageUrl(url)
	{
		this.image_url = url;
	}
	
	
	/**
	 * Returns image path
	 */
	getImage(path)
	{
		return this.image_url + "/" + path;
	}
	
	
	/**
	 * Show edit
	 */
	showEdit(chat_id)
	{
		this.show_dialog = "edit";
		this.show_dialog_id = chat_id;
		this.current_chat_id = chat_id;
	}
	
	
	/**
	 * Show delete
	 */
	showDelete(chat_id)
	{
		this.show_dialog = "delete";
		this.show_dialog_id = chat_id;
		this.current_chat_id = chat_id;
	}
	
	
	/**
	 * Delete chat
	 */
	async deleteChat(chat_id)
	{
		/* Find chat by id */
		var chat_pos = this.findChat(chat_id);
		if (chat_pos == -1) return;
		
		/* Get chat */
		var chat = this.chats[chat_pos];
		if (!chat) return;
		
		/* Remove chat */
		this.chats.splice(chat_pos, 1);
		
		/* Select new chat */
		if (this.current_chat_id == chat_id)
		{
			this.selectChat(chat_pos);
		}
		
		/* Send api */
		await sendApi("/api/chat/delete", {
			chat_id: chat.id,
		});
	}
	
	
	/**
	 * Rename chat
	 */
	async renameChat(chat_id, new_name)
	{
		/* Find chat by id */
		var chat = this.findChatById(chat_id);
		if (!chat) return;
		
		/* Rename title */
		chat.title = new_name;
		
		/* Send api */
		await sendApi("/api/chat/rename", {
			chat_id: chat.id,
			title: new_name,
		});
	}
	
	
	/**
	 * Send message
	 */
	async sendMessage(chat_id, message)
	{
		/* Find chat by id */
		var chat = this.findChatById(chat_id);
		if (!chat)
		{
			chat = new ChatHistory();
			chat.id = Date.now();
			chat.title = "Chat " + chat.id;
			this.chats.push(chat);
		}
		
		/* Create message */
		var item = new ChatMessage()
		item.sender = "human";
		item.content = [
			{
				"block": "text",
				"content": message,
			}
		];
		
		/* Add message to history */
		chat.addMessage(item);
		this.selectItem(chat.id);
		
		/* Send api */
		await sendApi("/api/chat/send", {
			chat_id: chat.id,
			message: message,
		});
	}
	
	
	/**
	 * Load
	 */
	async load()
	{
		var result = await sendApi("/api/chat/load");
		if (result.isSuccess())
		{
			this.is_loading = false;
			this.chats = [];
			for (var i=0; i<result.data.items.length; i++)
			{
				var item = result.data.items[i];
				var history = new ChatHistory();
				history.assign(item);
				this.chats.push(history);
			}
		}
	}
}

export default ChatPageModel;