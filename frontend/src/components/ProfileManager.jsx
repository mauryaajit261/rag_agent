import { useState, useEffect } from 'react';
import { supabase } from '../supabaseClient';
import './ProfileManager.css';

function ProfileManager({ session }) {
    const [loading, setLoading] = useState(true);
    const [profile, setProfile] = useState({
        full_name: '',
        company_name: '',
        job_title: '',
        bio: '',
        avatar_url: ''
    });
    const [saveStatus, setSaveStatus] = useState('');

    useEffect(() => {
        if (session?.user) {
            getProfile();
        }
    }, [session]);

    async function getProfile() {
        try {
            setLoading(true);
            const { user } = session;

            const { data, error } = await supabase
                .from('profiles')
                .select(`full_name, company_name, job_title, bio, avatar_url`)
                .eq('id', user.id)
                .single();

            if (error) {
                // If profile doesn't exist, it might not be an error just zero rows
                if (error.code !== 'PGRST116') {
                    console.error('Error fetching profile:', error);
                }
            } else if (data) {
                setProfile({
                    full_name: data.full_name || '',
                    company_name: data.company_name || '',
                    job_title: data.job_title || '',
                    bio: data.bio || '',
                    avatar_url: data.avatar_url || ''
                });
            }
        } catch (error) {
            console.error('Error in getProfile:', error.message);
        } finally {
            setLoading(false);
        }
    }

    async function updateProfile(e) {
        e.preventDefault();
        try {
            setLoading(true);
            setSaveStatus('');
            const { user } = session;

            const updates = {
                id: user.id,
                full_name: profile.full_name,
                company_name: profile.company_name,
                job_title: profile.job_title,
                bio: profile.bio,
                avatar_url: profile.avatar_url,
                updated_at: new Date(),
            };

            const { error } = await supabase.from('profiles').upsert(updates);

            if (error) {
                throw error;
            }
            
            setSaveStatus('Profile updated successfully!');
            setTimeout(() => setSaveStatus(''), 3000);
        } catch (error) {
            setSaveStatus('Error updating profile: ' + error.message);
        } finally {
            setLoading(false);
        }
    }

    const handleChange = (e) => {
        const { name, value } = e.target;
        setProfile(prev => ({
            ...prev,
            [name]: value
        }));
    };

    if (loading && !profile.full_name && !profile.company_name) {
        return <div className="profile-container loading">Loading profile...</div>;
    }

    return (
        <div className="profile-container">
            <div className="profile-header">
                <h2>User Profile</h2>
                <p>Manage your personal and professional details.</p>
            </div>

            <div className="profile-card">
                <form onSubmit={updateProfile} className="profile-form">
                    
                    <div className="form-group">
                        <label htmlFor="email">Email</label>
                        <input
                            id="email"
                            type="text"
                            value={session.user.email}
                            disabled
                            className="input-disabled"
                        />
                        <span className="help-text">Email address is bound to your account credentials.</span>
                    </div>

                    <div className="form-group">
                        <label htmlFor="full_name">Full Name</label>
                        <input
                            id="full_name"
                            name="full_name"
                            type="text"
                            value={profile.full_name}
                            onChange={handleChange}
                            placeholder="John Doe"
                        />
                    </div>

                    <div className="form-row">
                        <div className="form-group">
                            <label htmlFor="company_name">Company Name</label>
                            <input
                                id="company_name"
                                name="company_name"
                                type="text"
                                value={profile.company_name}
                                onChange={handleChange}
                                placeholder="mySetu"
                            />
                        </div>

                        <div className="form-group">
                            <label htmlFor="job_title">Job Title</label>
                            <input
                                id="job_title"
                                name="job_title"
                                type="text"
                                value={profile.job_title}
                                onChange={handleChange}
                                placeholder="Software Engineer"
                            />
                        </div>
                    </div>

                    <div className="form-group">
                        <label htmlFor="bio">Bio</label>
                        <textarea
                            id="bio"
                            name="bio"
                            value={profile.bio}
                            onChange={handleChange}
                            placeholder="A brief description about yourself"
                            rows="4"
                        />
                    </div>

                    <div className="form-actions">
                        <button type="submit" className="btn-primary" disabled={loading}>
                            {loading ? 'Saving...' : 'Save Profile'}
                        </button>
                        {saveStatus && (
                            <span className={`status-message ${saveStatus.includes('Error') ? 'error' : 'success'}`}>
                                {saveStatus}
                            </span>
                        )}
                    </div>
                </form>
            </div>
        </div>
    );
}

export default ProfileManager;
