import React, { Component } from 'react';
import autobahn from 'autobahn';
import './App.css';

class App extends Component {
  constructor() {
    super();

    this.connection = new autobahn.Connection({
      url: `ws://${window.location.host}/ws`,
      //url: `ws://raspberrypi.local:8080/ws`,
      realm: 'realm1',
      max_retries: -1,  // unlimited
      max_retry_delay: 10,
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
    this.connection.onclose = () => {
      this.setState({'session': null});
    };

    this.connection.open();
  }

  render() {
    return (
      <div className="App">
        <header className="App__header">Pullup Standup</header>

        {this.state.session
          ?
            [<CurrentUser session={this.state.session}
                         user={this.state.current_user}
                         enroll_mode={this.state.enroll_mode}
            />,
            this.state.current_user ?
              <CurrentPullups session={this.state.session} data={this.state.pullup} />
              : null]
          : <h2>Disconnected.</h2>}
      </div>
    );
  }
}

export default App;


class CurrentUser extends Component {
  render() {
    if (this.props.user) {
      return (
        <div className="CurrentUser">
          <div className="CurrentUser__pfpic-wrap">
            <img src={this.props.user.pfpic || "http://placehold.it/200x200"}
                 className="CurrentUser__pfpic" />
          </div>
          <div className="CurrentUser__info">
            <div className="CurrentUser__name">{this.props.user.name}</div>
            <div className="CurrentUser__username">{this.props.user.username}</div>
            <div className="CurrentUser__record">
              This week: <span>{this.props.user.total_this_week}</span> |
              Record: <span>{this.props.user.best_this_week}</span>
            </div>
            <div className="CurrentUser__record">
              Total ever: <span>{this.props.user.total_lifetime}</span> |
              Record: <span>{this.props.user.best_lifetime}</span>
            </div>
          </div>
        </div>
      );
    } else if (this.props.enroll_mode) {
      return <Enrollment session={this.props.session} />;
    } else {
      return <div className="CurrentUser__signedout">Tap your badge to play!</div>;
    }
  }
}


class CurrentPullups extends Component {
  constructor() {
    super();
    this.endSet = this.endSet.bind(this);
    this.signout = this.signout.bind(this);
  }
  endSet() {
    console.log('End set');
    this.props.session.call('pusu.end_set');
  }
  signout() {
    console.log('Sign out');
    this.props.session.call('pusu.signout');
  }

  render() {
    if (this.props.data) {
      return (
        <div className="CurrentPullups">
          <div className="CurrentPullups__content">
            <div className={`CurrentPullups__rawBar CurrentPullups__rawBar_${this.props.data.state}`}
                 style={{height: this.props.data.raw_value / 32768.0 * 100 + '%'}}/>
            <div className="CurrentPullups__pullups">{this.props.data.pullups}</div>
            <div className="CurrentPullups__set-time">{
              this.props.data.state == 'IDLE'
              ? this.props.data.time_in_set.toFixed(1)
              : this.props.data.time_since_start.toFixed(1)
            } sec</div>
          </div>

          <div className="CurrentPullups__done">
            { this.props.data.state == 'IDLE'
              ?
              <div className="CurrentPullups__done_btn CurrentPullups__done_btn_signout" onClick={this.signout}>Sign out &raquo;</div>
              :
              <div className="CurrentPullups__done_btn CurrentPullups__done_btn_end_set" onClick={this.endSet}>
                <div className="CurrentPullups__done_btn__countdown"
                     style={{width: (1 - this.props.data.idle_time_percent) * 100 + '%'}} />
                <div>Finish set &raquo;</div>
              </div>
            }
          </div>
        </div>
      );
    }
    return <div />;
  }
}


class Enrollment extends Component {
  constructor() {
    super();
    this.state = {'username': ''};
    this.handleChange = this.handleChange.bind(this);
    this.enroll = this.enroll.bind(this);
    this.cancel = this.cancel.bind(this);
  }
  componentDidMount() {
    this.usernameInput.focus();
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
            <input type="text" value={this.state.username} onChange={this.handleChange}
              ref={(input) => { this.usernameInput = input; } }/>
            <button onClick={this.enroll} disabled={!this.state.username}>Register</button>
            <button onClick={this.cancel}>Cancel</button>
          </form>
        </div>
    );
  }
}
