import React, { useState } from 'react';
import { GoogleLogin } from '@react-oauth/google';
import { useDispatch, useSelector } from 'react-redux';
import type { RootState } from '../store/store';
import { loginSuccess, logout } from '../features/authSlice';
import { useNavigate } from 'react-router-dom';
import apiClient from '../api/axios';
import { Swords, Users, Crown, LogOut, User, Plus, ArrowRight, Sparkles } from 'lucide-react';

const Home: React.FC = () => {
  const user = useSelector((state: RootState) => state.auth.user);
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const [roomCode, setRoomCode] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState('');

  const handleGoogleSuccess = async (credentialResponse: any) => {
    try {
      const res = await apiClient.post('/api/auth/google', {
        credential: credentialResponse.credential,
      });
      dispatch(loginSuccess({
        id: res.data.user_id,
        username: res.data.username,
        token: res.data.access_token,
      }));
    } catch (error) {
      console.error('Login Failed', error);
    }
  };

  const createRoom = async () => {
    setIsCreating(true);
    setError('');
    try {
      const res = await apiClient.post('/api/games');
      navigate(`/game/${res.data.room_code}`);
    } catch (err: any) {
      setError('Failed to create game. Please try again.');
      console.error('Failed to create room', err);
    } finally {
      setIsCreating(false);
    }
  };

  const joinRoom = () => {
    if (roomCode.trim().length >= 4) {
      navigate(`/game/${roomCode.trim().toUpperCase()}`);
    }
  };

  return (
    <div className="min-h-screen gradient-bg flex flex-col">
      {/* Nav */}
      <nav className="w-full px-6 py-4 flex items-center justify-between border-b border-zinc-800/50">
        <div className="flex items-center gap-2">
          <span className="text-2xl">♟️</span>
          <span className="text-xl font-bold text-white">Pawnly</span>
        </div>
        {user && (
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/profile')}
              className="flex items-center gap-2 text-zinc-400 hover:text-white transition-colors text-sm"
            >
              <User size={16} />
              <span className="hidden sm:inline">{user.username.split('@')[0]}</span>
            </button>
            <button
              onClick={() => dispatch(logout())}
              className="flex items-center gap-1 text-zinc-500 hover:text-red-400 transition-colors text-sm"
            >
              <LogOut size={14} />
            </button>
          </div>
        )}
      </nav>

      {/* Main */}
      <main className="flex-1 flex flex-col items-center justify-center px-4 py-12">
        {/* Hero */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-emerald-500/10 border border-emerald-500/20 rounded-full text-emerald-400 text-xs font-medium mb-6">
            <Sparkles size={12} />
            Real-time multiplayer chess
          </div>
          <h1 className="text-5xl sm:text-7xl font-extrabold text-white mb-4 tracking-tight">
            Pawn<span className="text-emerald-400">ly</span>
          </h1>
          <p className="text-lg text-zinc-500 max-w-md mx-auto">
            Play chess with friends. Create a room, share the code, and start playing instantly.
          </p>
        </div>

        {!user ? (
          /* ── Login Card ── */
          <div className="card max-w-sm w-full text-center">
            <div className="w-16 h-16 bg-zinc-800 rounded-2xl flex items-center justify-center mx-auto mb-6">
              <Crown size={32} className="text-emerald-400" />
            </div>
            <h2 className="text-xl font-bold text-white mb-2">Welcome</h2>
            <p className="text-zinc-500 text-sm mb-8">Sign in with Google to start playing</p>
            <div className="flex justify-center">
              <GoogleLogin
                onSuccess={handleGoogleSuccess}
                onError={() => console.log('Login Failed')}
                theme="filled_black"
                shape="pill"
                size="large"
              />
            </div>
          </div>
        ) : (
          /* ── Game Actions ── */
          <div className="w-full max-w-lg space-y-4">
            {error && (
              <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-sm px-4 py-3 rounded-xl text-center">
                {error}
              </div>
            )}

            {/* Create Game */}
            <div className="card-hover group" onClick={createRoom}>
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 bg-emerald-500/10 border border-emerald-500/20 rounded-xl flex items-center justify-center group-hover:bg-emerald-500/20 transition-colors">
                  <Plus size={24} className="text-emerald-400" />
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-bold text-white flex items-center gap-2">
                    New Game
                    {isCreating && (
                      <span className="inline-block w-4 h-4 border-2 border-emerald-400 border-t-transparent rounded-full animate-spin" />
                    )}
                  </h3>
                  <p className="text-zinc-500 text-sm">Create a room and invite a friend</p>
                </div>
                <ArrowRight size={20} className="text-zinc-600 group-hover:text-emerald-400 transition-colors" />
              </div>
            </div>

            {/* Join Game */}
            <div className="card">
              <div className="flex items-center gap-4 mb-4">
                <div className="w-14 h-14 bg-blue-500/10 border border-blue-500/20 rounded-xl flex items-center justify-center">
                  <Users size={24} className="text-blue-400" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white">Join Game</h3>
                  <p className="text-zinc-500 text-sm">Enter a room code from your friend</p>
                </div>
              </div>
              <div className="flex gap-3">
                <input
                  type="text"
                  placeholder="Room code"
                  className="flex-1 bg-zinc-800/80 border border-zinc-700 rounded-xl px-4 py-3 text-white font-mono text-center text-lg tracking-widest uppercase
                             placeholder:text-zinc-600 placeholder:font-sans placeholder:text-sm placeholder:tracking-normal placeholder:normal-case
                             focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/20 transition-all"
                  value={roomCode}
                  onChange={(e) => setRoomCode(e.target.value.toUpperCase())}
                  maxLength={6}
                  onKeyDown={(e) => e.key === 'Enter' && joinRoom()}
                />
                <button
                  className="btn-primary !px-8 !rounded-xl"
                  onClick={joinRoom}
                  disabled={roomCode.trim().length < 4}
                >
                  Join
                </button>
              </div>
            </div>

            {/* Quick Links */}
            <div className="flex items-center justify-center gap-6 pt-4 text-sm">
              <button
                onClick={() => navigate('/profile')}
                className="text-zinc-500 hover:text-white transition-colors flex items-center gap-1.5"
              >
                <User size={14} /> Profile
              </button>
              <span className="text-zinc-800">•</span>
              <button className="text-zinc-500 hover:text-white transition-colors flex items-center gap-1.5">
                <Crown size={14} /> Leaderboard
              </button>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="text-center text-zinc-700 text-xs py-6 border-t border-zinc-800/30">
        Built with ♟️ — Pawnly
      </footer>
    </div>
  );
};

export default Home;
