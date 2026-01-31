import './Body.css';
import {useState} from "react";
import {useEffect} from "react";
import api from '../api.js'

function MainBody() {
  const [activeId, setActiveId] = useState(0);
  const [players, setPlayers] = useState([]);

  useEffect(() => {
    fetchPlayers();
  }, [activeId]);

  const fetchPlayers = async () => {
    try {
      const response = await api.get("/", {
        params: {
          position: activeId
        }
      });

      setPlayers(response.data);
    } catch (error) {
      console.error("Error fetching players", error);
    }
  };

  return (
    <div className="body">
      <h1 className="title">Top 10 Predicted Scorers</h1>

      <PositionFilter
        activeId={activeId}
        setActiveId={setActiveId}
      />

      <br />

      <div className="players-list">
        {players.map((player, index) => (
          <PlayerInfo
            key = {player["player_id"]}
            player = {player}
            index = {index}
          />
        ))}
      </div>
    </div>
  );
}

function PositionFilter({ activeId, setActiveId }) {
    const buttons = [
        {id: 0, label: "All"},
        {id: 1, label: "GK"},
        {id: 2, label: "DEF"},
        {id: 3, label: "MID"},
        {id: 4, label: "ATT"}
    ];

    return (
        <div className="filter-container">
            <div className="buttons">
                {buttons.map(btn => (
                    <button
                        key={btn.id}
                        className={activeId === btn.id ? "filter-button active" : "filter-button"}
                        onClick={() => setActiveId(btn.id)}
                    > {btn.label}
                    </button>
                ))}
            </div>
        </div>
    );
}




function PlayerInfo({ player,index}) {
    const positionDict = {
        1: 'GK',
        2: 'DEF',
        3: 'MID',
        4: 'ATT'
    }
    return (
        <div className="player-container">

            {/* name + ranking row */}
            <div className="name-row">
                <h3 className="player-name">{player["web_name"]}</h3>
                <span className="card-rank">#{index+1}</span>
            </div>

            {/* team + position */}
            <div className="player-meta">
                <span className="team">{player["short_name"]}</span>
                <span className="position">{positionDict[player["element_type"]]}</span>
            </div>

            {/* stats row */}
            <div className="stats-row">

                <div className="stat-box">
                    <span className="points-value">
                        {(player["predicted_points"]).toFixed(2)}
                    </span>
                    <span className="points-label">
                        predicted pts
                    </span>
                </div>

                <div className="stat-box">
                    <span className="points-value">
                        {player["points_last_gw"]}
                    </span>
                    <span className="points-label">
                        pts last gw
                    </span>
                </div>

                <div className="stat-box">
                    <span className="points-value">
                        {player["ict_index"]}
                    </span>
                    <span className="points-label">
                        form
                    </span>
                </div>

            </div>
        </div>
    );
}


export default MainBody;