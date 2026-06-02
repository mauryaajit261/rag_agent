-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ==============================================================================
-- 1. CHATS TABLE
-- ==============================================================================
CREATE TABLE chats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    title TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable Row Level Security (RLS) for chats
ALTER TABLE chats ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only select/read their own chats
CREATE POLICY "Users can view their own chats" 
ON chats FOR SELECT 
USING (auth.uid() = user_id);

-- Policy: Users can only insert their own chats
CREATE POLICY "Users can create their own chats" 
ON chats FOR INSERT 
WITH CHECK (auth.uid() = user_id);

-- Policy: Users can only delete their own chats
CREATE POLICY "Users can delete their own chats" 
ON chats FOR DELETE 
USING (auth.uid() = user_id);

-- Policy: Users can only update their own chats
CREATE POLICY "Users can update their own chats" 
ON chats FOR UPDATE 
USING (auth.uid() = user_id);


-- ==============================================================================
-- 2. MESSAGES TABLE
-- ==============================================================================
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chat_id UUID REFERENCES chats(id) ON DELETE CASCADE NOT NULL,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable Row Level Security (RLS) for messages
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only view messages belonging to their chats
CREATE POLICY "Users can view their own messages" 
ON messages FOR SELECT 
USING (auth.uid() = user_id);

-- Policy: Users can only insert messages into their own chats
CREATE POLICY "Users can insert their own messages" 
ON messages FOR INSERT 
WITH CHECK (auth.uid() = user_id);

-- Policy: Users can delete their own messages
CREATE POLICY "Users can delete their own messages" 
ON messages FOR DELETE 
USING (auth.uid() = user_id);


-- ==============================================================================
-- 3. INDEXES (For Performance Optimization)
-- ==============================================================================
-- Index to quickly load all chats for a specific user
CREATE INDEX idx_chats_user_id ON chats(user_id);

-- Index to quickly load entirely a specific chat history
CREATE INDEX idx_messages_chat_id ON messages(chat_id);

-- Index to sort messages by creation time during retrieval
CREATE INDEX idx_messages_created_at ON messages(created_at);

-- ==============================================================================
-- 4. PROFILES TABLE
-- ==============================================================================
CREATE TABLE profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name TEXT,
    company_name TEXT,
    job_title TEXT,
    bio TEXT,
    avatar_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable Row Level Security (RLS) for profiles
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only view their own profile
CREATE POLICY "Users can view their own profile" 
ON profiles FOR SELECT 
USING (auth.uid() = id);

-- Policy: Users can insert their own profile
CREATE POLICY "Users can insert their own profile" 
ON profiles FOR INSERT 
WITH CHECK (auth.uid() = id);

-- Policy: Users can update their own profile
CREATE POLICY "Users can update their own profile" 
ON profiles FOR UPDATE 
USING (auth.uid() = id);

-- Create a trigger function to automatically set updated_at
CREATE OR REPLACE FUNCTION handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
   NEW.updated_at = NOW();
   RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to automate updated_at timestamp updates
CREATE TRIGGER set_profiles_updated_at
BEFORE UPDATE ON profiles
FOR EACH ROW
EXECUTE FUNCTION handle_updated_at();

-- Trigger to automatically create a profile for a new user
CREATE OR REPLACE FUNCTION public.handle_new_user() 
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.profiles (id, full_name)
  VALUES (new.id, new.raw_user_meta_data->>'full_name');
  RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();
