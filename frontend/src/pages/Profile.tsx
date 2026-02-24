import React, { useEffect, useState } from 'react';
import { useSelector } from 'react-redux';
import type { RootState } from '../store/store';
import { useNavigate } from 'react-router-dom';
import apiClient from '../api/axios';
import { User, Crown, ArrowLeft, Swords, Trophy, TrendingUp, Bot } from 'lucide-react';
import { format } from 'date-fns';

interface GameRecord {
  id: number;
  status: string;
  winner_id: number | null;
  is_bot_game?: boolean;
  bot_difficulty?: string | null;
  created_at: string;
  white_player: { id: number; username: string; elo_rating: number } | null;
  black_player: { id: number; username: string; elo_rating: number } | null;
}

interface UserProfile {
  id: number;
  username: string;
  elo_rating: number;
  bot_elo: number | null;
  created_at: string;
}

const Profile: React.FC = () => {
  const user = useSelector((state: RootState) => state.auth.user);
  const navigate = useNavigate();
  const [games, setGames] = useState<GameRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [profile, setProfile] = useState<UserProfile | null>(null);

  useEffect(() => {
    if (user) {
      apiClient.get(`/api/users/${user.id}/games`)
        .then(res => setGames(res.data))
        .catch(console.error)
        .finally(() => setLoading(false));
      apiClient.get('/api/users/me')
        .then(res => setProfile(res.data))
        .catch(console.error);
    }
  }, [user]);

  if (!user) {
    navigate('/');
    return null;
  }

  const wins = games.filter(g => g.winner_id === user.id).length;
  const losses = games.filter(g => g.winner_id && g.winner_id !== user.id).length;
  const draws = games.filter(g => g.status === 'finished' && !g.winner_id).length;

  return (
    <div className="min-h-screen gradient-bg flex flex-col">
      {/* Nav */}
      <nav className="w-full px-6 py-4 flex items-center justify-between border-b border-zinc-800/50">
        <button onClick={() => navigate('/')} className="flex items-center gap-2 text-zinc-400 hover:text-white transition-colors text-sm">
          <ArrowLeft size={16} /> Back
        </button>
        <span className="text-xl font-bold text-white flex items-center gap-2">
          <span className="text-lg">♟️</span> Pawnly
        </span>
        <div className="w-16" />
      </nav>

      <main className="flex-1 max-w-3xl mx-auto w-full px-4 py-8">
        {/* Profile Header */}
        <div className="card mb-6">
          <div className="flex items-center gap-5">
            <div className="w-20 h-20 bg-zinc-800 rounded-2xl flex items-center justify-center border border-zinc-700">
              <User size={36} className="text-zinc-500" />
            </div>
            <div className="flex-1">
              <h1 className="text-2xl font-bold text-white">{user.username.split('@')[0]}</h1>
              <p className="text-zinc-500 text-sm">{user.username}</p>
            </div>
          </div>
        </div>

        {/* Elo Ratings */}
        <div className="grid grid-cols-2 gap-3 mb-4">
          <div className="card text-center">
            <Crown size={20} className="text-emerald-400 mx-auto mb-2" />
            <p className="text-2xl font-bold text-white">{profile?.elo_rating ?? '—'}</p>
            <p className="text-zinc-500 text-xs">Human Elo</p>
          </div>
          <div className="card text-center">
            <Bot size={20} className="text-orange-400 mx-auto mb-2" />
            <p className="text-2xl font-bold text-white">{profile?.bot_elo ?? '—'}</p>
            <p className="text-zinc-500 text-xs">Bot Elo</p>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-3 mb-6">
          <div className="card text-center">
            <Trophy size={20} className="text-emerald-400 mx-auto mb-2" />
            <p className="text-2xl font-bold text-white">{wins}</p>
            <p className="text-zinc-500 text-xs">Wins</p>
          </div>
          <div className="card text-center">
            <Swords size={20} className="text-red-400 mx-auto mb-2" />
            <p className="text-2xl font-bold text-white">{losses}</p>
            <p className="text-zinc-500 text-xs">Losses</p>
          </div>
          <div className="card text-center">
            <TrendingUp size={20} className="text-blue-400 mx-auto mb-2" />
            <p className="text-2xl font-bold text-white">{draws}</p>
            <p className="text-zinc-500 text-xs">Draws</p>
          </div>
        </div>

        {/* Game History */}
        <div className="card">
          <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-4 flex items-center gap-2">
            <Crown size={14} /> Recent Games
          </h2>

          {loading ? (
            <div className="text-center py-8">
              <span className="inline-block w-6 h-6 border-2 border-emerald-400 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : games.length === 0 ? (
            <div className="text-center py-8 text-zinc-600">
              <Swords size={32} className="mx-auto mb-3 opacity-40" />
              <p>No games played yet</p>
              <button onClick={() => navigate('/')} className="btn-primary mt-4 !py-2 !px-4 text-sm">
                Play your first game
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              {games.map(g => {
                const isWin = g.winner_id === user.id;
                const isBot = g.is_bot_game;
                const isDraw = g.status === 'finished' && !g.winner_id && !isBot;

                let opponent: string | undefined;
                if (isBot) {
                  const diffLabel = g.bot_difficulty
                    ? g.bot_difficulty.charAt(0).toUpperCase() + g.bot_difficulty.slice(1)
                    : 'Bot';
                  opponent = `🤖 Bot (${diffLabel})`;
                } else {
                  opponent = g.white_player?.id === user.id
                    ? g.black_player?.username
                    : g.white_player?.username;
                  if (opponent) opponent = opponent.split('@')[0];
                }

                const resultColor = isWin ? 'bg-emerald-400' : (isDraw ? 'bg-zinc-500' : 'bg-red-400');
                const resultLabel = isWin ? 'Win' : isDraw ? 'Draw' : 'Loss';
                const resultTextColor = isWin ? 'text-emerald-400' : isDraw ? 'text-zinc-500' : 'text-red-400';

                return (
                  <div key={g.id} className="flex items-center gap-3 p-3 rounded-xl bg-zinc-800/40 hover:bg-zinc-800/70 transition-colors">
                    <div className={`w-2 h-8 rounded-full ${resultColor}`} />
                    <div className="flex-1 min-w-0">
                      <p className="text-white font-medium text-sm truncate">
                        vs {opponent || '—'}
                      </p>
                      <p className={`text-xs ${resultTextColor}`}>
                        {resultLabel}
                      </p>
                    </div>
                    <span className="text-zinc-600 text-xs">{format(new Date(g.created_at), 'MMM d')}</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </main>
    </div>
  );
};

export default Profile;
