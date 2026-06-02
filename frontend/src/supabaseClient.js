import { createClient } from '@supabase/supabase-js';

// Loaded from frontend/.env (VITE_*). The Supabase anon key is designed to be
// public (RLS protects it), so it is safe to ship in the client bundle.
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseAnonKey) {
    throw new Error('Missing VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY — check frontend/.env');
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
