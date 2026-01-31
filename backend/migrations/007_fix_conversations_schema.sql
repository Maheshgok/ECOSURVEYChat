-- Fix conversations table schema to match Phase 7 implementation
-- Add missing columns that chat.py expects

-- Messages table: Add missing metadata column
ALTER TABLE messages
ADD COLUMN IF NOT EXISTS message_metadata JSONB DEFAULT '{}';

CREATE INDEX IF NOT EXISTS idx_messages_metadata ON messages USING GIN (message_metadata);

-- Conversations table: Add missing columns
ALTER TABLE conversations
ADD COLUMN IF NOT EXISTS chat_session_id UUID,
ADD COLUMN IF NOT EXISTS user_id UUID,
ADD COLUMN IF NOT EXISTS user_pseudo_id VARCHAR(256),
ADD COLUMN IF NOT EXISTS session_metadata JSONB DEFAULT '{}';

-- Add foreign key constraint for user_id (ignore if already exists)
DO $$
BEGIN
    ALTER TABLE conversations
    ADD CONSTRAINT conversations_user_id_fk 
      FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN
    -- Constraint already exists, ignore
END;
$$;

-- Create index for user_id lookups
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);

-- Create index for user_pseudo_id lookups
CREATE INDEX IF NOT EXISTS idx_conversations_user_pseudo_id ON conversations(user_pseudo_id);

-- Comments
COMMENT ON COLUMN messages.message_metadata IS 'Additional message metadata (intuition, evidence, followups)';
COMMENT ON COLUMN conversations.chat_session_id IS 'Reference to chat session for grouping conversations';
COMMENT ON COLUMN conversations.user_id IS 'Reference to user who initiated conversation';
COMMENT ON COLUMN conversations.user_pseudo_id IS 'Hashed user ID for privacy';
COMMENT ON COLUMN conversations.session_metadata IS 'Additional session metadata stored as JSON';
