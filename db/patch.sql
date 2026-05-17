-- Update table ai_notes
ALTER TABLE `ai_notes`
ADD COLUMN `android_id` BIGINT DEFAULT NULL AFTER `space_id`, 
ADD COLUMN `user_id` BIGINT DEFAULT NULL AFTER `android_id`, 
ADD COLUMN `type` VARCHAR(255) NOT NULL DEFAULT 'note' AFTER `user_id`,
CHANGE `category_id` BIGINT NULL AFTER `type`,
ADD INDEX `idx_android_id` (`android_id`),
ADD INDEX `idx_user_id` (`user_id`),
ADD INDEX `idx_type` (`type`),
ADD FOREIGN KEY (`android_id`) REFERENCES `ai_androids` (`id`) ON UPDATE CASCADE ON DELETE CASCADE,
ADD FOREIGN KEY (`user_id`) REFERENCES `cabinet_users` (`id`) ON UPDATE CASCADE ON DELETE CASCADE;
UPDATE `ai_notes` AS n INNER JOIN `ai_note_categories` AS c ON n.category_id = c.id SET n.android_id = c.android_id, n.user_id = c.user_id, n.type = c.type;

-- Remove columns from table ai_note_categories
ALTER TABLE `ai_note_categories`
DROP FOREIGN KEY `ai_note_categories_ibfk_2`,
DROP COLUMN `android_id`,
DROP COLUMN `user_id`,
DROP COLUMN `type`;

ALTER TABLE `ai_chats`
ADD `android_id` BIGINT NULL AFTER `title`
ADD `user_id` BIGINT NULL AFTER `android_id`
ADD FOREIGN KEY (`android_id`) REFERENCES `ai_androids` (`id`) ON UPDATE CASCADE ON DELETE SET NULL,
ADD FOREIGN KEY (`user_id`) REFERENCES `cabinet_users` (`id`) ON UPDATE CASCADE ON DELETE SET NULL;

ALTER TABLE `ai_chats`
ADD `space_id` BIGINT NOT NULL AFTER `title`
ADD FOREIGN KEY (`space_id`) REFERENCES `ai_space` (`id`) ON UPDATE CASCADE ON DELETE RESTRICT;

ALTER TABLE `ai_chats`
ADD `gmtime_edit` DATETIME NOT NULL AFTER `gmtime_add`;

ALTER TABLE `ai_models`
ADD `delay` BIGINT NOT NULL DEFAULT 5000 AFTER `timeout`;

ALTER TABLE `ai_providers`
CHANGE `code` `type` VARCHAR(255) NOT NULL;

ALTER TABLE `ai_providers`
ADD `models` JSON DEFAULT NULL AFTER `config`;