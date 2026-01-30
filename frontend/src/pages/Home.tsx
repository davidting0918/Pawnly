// The Home.tsx, Game.tsx, and Profile.tsx files are large.
// I will reuse the content I generated before, but write them one by one.
// Writing Home.tsx first.
import React, { useState } from 'react';
import { GoogleLogin } from '@react-oauth/google';
import { useDispatch, useSelector } from 'react-redux';
import type { RootState } from '../store/store';
import { loginSuccess } from '../features/authSlice';
import { useNavigate } from 'react-router-dom';
import apiClient from '../api/axios';
import { Swords, Users } from 'lucide-react';

const Home: React.FC = () => {
  const user = useSelector((state: RootState) => state.auth.user);
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const [roomCode, setRoomCode] = useState('');

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
    try {
      const res = await apiClient.post('/api/games/create');
      const { room_code } = res.data;
      navigate(`/game/${room_code}`);
    } catch (error) {
      console.error("Failed to create room", error);
    }
  };

  const joinRoom = () => {
    if (roomCode.length === 6) {
      navigate(`/game/${roomCode}`);
    }
  };

  return (
    <div className="min-h-screen bg-pawnly-dark flex flex-col items-center justify-center text-white">
      <div className="text-center mb-12">
        <h1 className="text-6xl font-bold mb-4 flex items-center justify-center gap-4">
          <Swords size={64} className="text-pawnly-green" />
          Pawnly
        </h1>
        <p className="text-xl text-gray-400">Minimalist Real-time Chess</p>
      </div>

      {!user ? (
        <div className="bg-pawnly-board p-8 rounded-lg shadow-lg border border-gray-700">
          <p className="mb-6 text-center">Sign in to start playing</p>
          <div className="flex justify-center">
            <GoogleLogin
              onSuccess={handleGoogleSuccess}
              onError={() => console.log('Login Failed')}
              theme="filled_black"
              shape="pill"
            />
          </div>
        </div>
      ) : (
        <div className="space-y-6 w-full max-w-md">
          <div className="bg-pawnly-board p-6 rounded-lg border border-gray-700 hover:border-pawnly-green transition cursor-pointer" onClick={createRoom}>
            <h3 className="text-2xl font-bold mb-2 flex items-center gap-2">
              <Swords /> Play a Friend
            </h3>
            <p className="text-gray-400">Create a private room and share the code.</p>
          </div>

          <div className="bg-pawnly-board p-6 rounded-lg border border-gray-700">
            <h3 className="text-2xl font-bold mb-4 flex items-center gap-2">
              <Users /> Join Room
            </h3>
            <div className="flex gap-2">
              <input 
                type="text" 
                placeholder="Enter 6-digit code"
                className="flex-1 bg-gray-800 border border-gray-600 rounded px-4 py-2 text-white focus:outline-none focus:border-pawnly-green"
                value={roomCode}
                onChange={(e) => setRoomCode(e.target.value)}
                maxLength={6}
              />
              <button 
                className="bg-pawnly-green text-white px-6 py-2 rounded font-bold hover:bg-green-600 transition btn-3d"
                onClick={joinRoom}
              >
                Join
              </button>
            </div>
          </div>
          
          <div className="text-center text-gray-500 mt-8">
            Logged in as <span className="text-white">{user.username}</span>
            {' | '}
            <button onClick={() => navigate('/profile')} className="text-pawnly-green hover:underline">
              My Profile
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default Home;
