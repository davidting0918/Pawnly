// Writing Profile.tsx
import React, { useEffect, useState } from 'react';
import { useSelector } from 'react-redux';
import type { RootState } from '../store/store';
import apiClient from '../api/axios';
import { User, ShieldCheck, Calendar, BarChart3, Swords } from 'lucide-react';
import { format } from 'date-fns';

interface Game {
  id: number;
  status: string;
  winner_id: number | null;
  created_at: string;
  white_player: { username: string };
  black_player: { username: string };
}

const Profile: React.FC = () => {
  const currentUser = useSelector((state: RootState) => state.auth.user);
  const [games, setGames] = useState<Game[]>([]);

  useEffect(() => {
    if (currentUser) {
      apiClient.get(`/api/users/${currentUser.id}/games`)
        .then(response => setGames(response.data))
        .catch(console.error);
    }
  }, [currentUser]);

  if (!currentUser) return <div>Loading...</div>;

  return (
    <div className="min-h-screen bg-pawnly-dark text-white p-8">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center gap-6 mb-12">
          <div className="w-24 h-24 bg-pawnly-board rounded-full flex items-center justify-center border-4 border-gray-700">
            <User size={48} />
          </div>
          <div>
            <h1 className="text-4xl font-bold">{currentUser.username}</h1>
            <div className="flex items-center gap-4 text-gray-400 mt-2">
              <span className="flex items-center gap-2"><ShieldCheck size={16} /> ELO: 1200</span>
            </div>
          </div>
        </div>
        <h2 className="text-2xl font-bold mb-6 flex items-center gap-3"><BarChart3 /> Recent Games</h2>
        <div className="bg-pawnly-board rounded-lg border border-gray-700">
          <ul className="divide-y divide-gray-700">
            {games.map(game => (
              <li key={game.id} className="p-4 flex justify-between items-center">
                <div className="flex items-center gap-4">
                  <Swords className={game.winner_id === currentUser.id ? 'text-pawnly-green' : 'text-red-500'} />
                  <div>
                    <p className="font-bold">
                      vs {game.white_player?.username === currentUser.username ? game.black_player?.username : game.white_player?.username}
                    </p>
                    <p className={`text-sm ${game.winner_id === currentUser.id ? 'text-green-400' : 'text-red-400'}`}>
                      {game.winner_id === currentUser.id ? 'Win' : 'Loss'}
                    </p>
                  </div>
                </div>
                <span className="text-gray-400 text-sm">{format(new Date(game.created_at), 'yyyy-MM-dd')}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
};

export default Profile;
