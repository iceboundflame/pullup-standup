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
      'session': null,
      'pullup': null,
      'current_user': null,
      'enroll_mode': false,
    };

    this.connection.onopen = (session, details) => {
      this.setState({'session': session});

      session.subscribe("pusu.state", (e) => {
        console.log("pusu.state", e[0]);
        this.setState(e[0]);
      });

      session.call("pusu.get_state").then((e) => {
        console.log("pusu.get_state", e);
        this.setState(e);
      });
    };

    this.connection.open();
  }

  render() {
    return (
      <div>
        <h1>Pull-up Standup</h1>

        <CurrentUser session={this.state.session}
                     user={this.state.current_user}
                     enroll_mode={this.state.enroll_mode}
        />

        {this.state.current_user ? <CurrentPullups data={this.state.pullup} /> : null}
      </div>
    );
  }
}

class CurrentPullups extends React.Component {
  render() {
    if (this.props.data) {
      return (
        <div>
          <h2>{this.props.data.pullups}</h2>
          pull-ups done in <h3>{this.props.data.time_since_start.toFixed(1)} seconds</h3>
          Idle: <h3>{this.props.data.idle_time.toFixed(1)} seconds</h3>
        </div>
      );
    }
    return <div />;
  }
}

class CurrentUser extends React.Component {
  constructor() {
    super();
    this.signout = this.signout.bind(this);
  }
  signout() {
    console.log('Sign out');
    this.props.session.call('pusu.signout');
  }
  render() {
    if (this.props.user) {
      return (
        <div>
          Current User: {this.props.user.username} ({this.props.user.name})

          <ul>
            {this.props.user.records.map(record =>
              <li key={record.created_at}>{record.pullups} @ {record.created_at}</li>)}
          </ul>
          <button onClick={this.signout}>Sign out</button>
        </div>
      );
    } else if (this.props.enroll_mode) {
      return <Enrollment session={this.props.session} />;
    } else {
      return <h2>Present badge to begin</h2>;
    }
  }
}

class Enrollment extends React.Component {
  constructor() {
    super();
    this.state = {'username': 'a'};
    this.handleChange = this.handleChange.bind(this);
    this.enroll = this.enroll.bind(this);
    this.cancel = this.cancel.bind(this);
  }
  handleChange(event) {
    this.setState({'username': event.target.value});
  }
  enroll(event) {
    console.log('Enrolling', this.state.username, this.props.session);
    this.props.session.call('pusu.enroll', [this.state.username]);
    event.preventDefault();
  }
  cancel(event) {
    console.log('Cancel enroll', this.props.session);
    this.props.session.call('pusu.enroll', [null]);
    event.preventDefault();
  }
  render() {
    return (
        <div>
          <h2>Welcome new user! Please register:</h2>
          <form>
            <input type="text" value={this.state.username} onChange={this.handleChange} />
            <button onClick={this.enroll}>Register</button>
            <button onClick={this.cancel}>Cancel</button>
          </form>
        </div>
    );
  }
}

ReactDOM.render(<Content />, document.getElementById('content'));
