import './Body.css';
function MainBody (){

    const topPlayers = [
    { name: "Harry Kane", ranking: 1, team: "TOT", pos: "FWD", predicted: 8, last_gw_points: 6, form: 7 },
    { name: "Mohamed Salah", ranking: 2, team: "LIV", pos: "MID", predicted: 7, last_gw_points: 5, form: 6 },
    { name: "Kevin De Bruyne", ranking: 3, team: "MCI", pos: "MID", predicted: 6, last_gw_points: 4, form: 5 },
    { name: "Bruno Fernandes", ranking: 4, team: "MUN", pos: "MID", predicted: 6, last_gw_points: 7, form: 6 },
    { name: "Erling Haaland", ranking: 5, team: "MCI", pos: "FWD", predicted: 9, last_gw_points: 8, form: 9 },
    { name: "Son Heung-Min", ranking: 6, team: "TOT", pos: "FWD", predicted: 7, last_gw_points: 6, form: 7 },
    { name: "Trent Alexander-Arnold", ranking: 7, team: "LIV", pos: "DEF", predicted: 5, last_gw_points: 4, form: 6 },
    { name: "Rúben Dias", ranking: 8, team: "MCI", pos: "DEF", predicted: 5, last_gw_points: 5, form: 5 },
    { name: "David de Gea", ranking: 9, team: "MUN", pos: "GK", predicted: 4, last_gw_points: 6, form: 4 },
    { name: "Martin Ødegaard", ranking: 10, team: "ARS", pos: "MID", predicted: 6, last_gw_points: 5, form: 6 },
  ];
    return (
        <div className = 'body'>
            <h1 className='title'>Top 10 Predicted Scorers</h1>
            <PositionFilter/>
            <br />

            <div className="players-list">
                {topPlayers.map(player => (
                <PlayerInfo key={player.ranking} player={player} />
                ))}
            </div>
        </div>
    );
}

function PositionFilter() {
    return (
        <div className='filter-container'>
            <button className='filter-button active'>All</button>
            <button className='filter-button '>FWD</button>
            <button className='filter-button '>MID</button>
            <button className='filter-button'>DEF</button>
            <button className='filter-button'>GK</button>
        </div>
    )
}

function PlayerInfo({ player }) {
    return (
        <div className="player-container">

            {/* name + ranking row */}
            <div className="name-row">
                <h3 className="player-name">{player.name}</h3>
                <span className="card-rank">#{player.ranking}</span>
            </div>

            {/* team + position */}
            <div className="player-meta">
                <span className="team">{player.team}</span>
                <span className="position">{player.pos}</span>
            </div>

            {/* stats row */}
            <div className="stats-row">

                <div className="stat-box">
                    <span className="points-value">
                        {player.predicted}
                    </span>
                    <span className="points-label">
                        predicted pts
                    </span>
                </div>

                <div className="stat-box">
                    <span className="points-value">
                        {player.last_gw_points}
                    </span>
                    <span className="points-label">
                        last gw
                    </span>
                </div>

                <div className="stat-box">
                    <span className="points-value">
                        {player.form}
                    </span>
                    <span className="points-label">
                        form
                    </span>
                </div>

            </div>
        </div>
    );
}



function GetPlayerByPosition(players,position){
    if (position==='All'){
        return players
    }

    return players.filter(player => player.pos === position);

}

export default MainBody;