var React = require('react');
var ReactDOM = require('react-dom');

// var autobahn = require('autobahn');

class Content extends React.Component {
  constructor() {
    super();

    this.connection = new autobahn.Connection({
      url: `ws://${window.location.hostname}:8080/ws`,
      realm: 'realm1',
    });

    this.state = {
      pullups: 0,
      time_in_set: 0,
      idle_time: 0,
      user_profile: {
        name: "David",
        profile: {
          "thumbnail": "http://",
        },
        records: {
          "30 day": {id: 203, pullups: 12, time_in_set: 25},
          "all time": {id: 120, pullups: 19, time_in_set: 42},
        },
      },
    };

    this.connection.onopen = (session, details) => {
      session.subscribe("pusu.pullup", (e) => {
        console.log("pusu.pullup", e);
        this.setState(e[0]);
      });

      session.call("pusu.get_state").then((e) => {
        console.log("pusu.get_state", e);
        this.setState(e);
      });
    }

    this.connection.open();
  }

  render() {
    return (
      <div>
        <h1>Pull-up Standup</h1>
        <CurrentPullups data={this.state} />
      </div>
    );
  }
}

class CurrentPullups extends React.Component {
  render() {
    return (
      <div>
        <h2>{this.props.data.pullups}</h2>
        pull-ups done in <h3>{this.props.data.time_in_set.toFixed(1)} seconds</h3>
        Idle: <h3>{this.props.data.idle_time.toFixed(1)} seconds</h3>
      </div>
    );
  }
}

ReactDOM.render(<Content />, document.getElementById('content'));
