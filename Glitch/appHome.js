const axios = require("axios");
const qs = require("qs");

const JsonDB = require("node-json-db");
const db = new JsonDB("notes", true, false);

const apiUrl = "https://slack.com/api";

//db.delete("/");

/*
 * Home View - Use Block Kit Builder to compose: https://api.slack.com/tools/block-kit-builder
 */

const updateView = async user => {
  // Intro message -
  let blocks = [
    {
      "type": "section",
      "text": {
        "type": "plain_text",
        "text": "本日のMealsは・・・",
        "emoji": true
      }
    },
    {
      "type": "actions",
      "block_id": "KyLo",
      "elements": [
        {
          "type": "button",
          "action_id": "yes30_id",
          "text": {
            "type": "plain_text",
            "text": "ありmin30",
            "emoji": true
          },
          "value": "yes30"
        },
        {
          "type": "button",
          "action_id": "yes20_id",
          "text": {
            "type": "plain_text",
            "text": "ありmin20",
            "emoji": true
          },
          "value": "yes20"
        },
        {
          "type": "button",
          "action_id": "yes10_id",
          "text": {
            "type": "plain_text",
            "text": "ありmin10",
            "emoji": true
          },
          "value": "yes10"
        },
        {
          "type": "button",
          "action_id": "no_id",
          "text": {
            "type": "plain_text",
            "text": "なし",
            "emoji": true
          },
          "value": "no"
        }
      ]
    }
  ];

  // Append new data blocks after the intro -

  let newData = [];
  try {
    const rawData = db.getData(`/${user}/data/`);

    newData = rawData.slice().reverse(); // Reverse to make the latest first
    newData = newData.slice(0, 50); // Just display 20. BlockKit display has some limit.
  } catch (error) {
    //console.error(error);
  }
  if (newData) {
    let noteBlocks = [];

    for (const o of newData) {
      const color = o.color ? o.color : "yellow";

      let note = o.note;
      if (note.length > 3000) {
        note = note.substr(0, 2980) + "... _(truncated)_";
        console.log(note.length);
      }

      noteBlocks = [
        {
          type: "section",
          text: {
            type: "mrkdwn",
            text: note
          },
          accessory: {
            type: "image",
            image_url: `https://cdn.glitch.com/0d5619da-dfb3-451b-9255-5560cd0da50b%2Fstickie_${color}.png`,
            alt_text: "stickie note"
          }
        },
        {
          type: "context",
          elements: [
            {
              type: "mrkdwn",
              text: o.timestamp
            }
          ]
        },
        {
          type: "divider"
        }
      ];
      blocks = blocks.concat(noteBlocks);
    }
  }

  // The final view -

  let view = {
    type: "home",
    title: {
      type: "plain_text",
      text: "Keep notes!"
    },
    // blocks: blocks
    blocks: blocks
  };

  return JSON.stringify(view);
};


const updateViewOtherStaff = async user => {
  // Intro message -
  let blocks = [
    {
      type: "section",
      text: {
        type: "plain_text",
        text: "上部メッセージタブを確認してください:knife_fork_plate:",
        emoji: true
      }
    }
  ];

  // Append new data blocks after the intro -

  let newData = [];
  try {
    const rawData = db.getData(`/${user}/data/`);

    newData = rawData.slice().reverse(); // Reverse to make the latest first
    newData = newData.slice(0, 50); // Just display 20. BlockKit display has some limit.
  } catch (error) {
    //console.error(error);
  }
  if (newData) {
    let noteBlocks = [];

    for (const o of newData) {
      const color = o.color ? o.color : "yellow";

      let note = o.note;
      if (note.length > 3000) {
        note = note.substr(0, 2980) + "... _(truncated)_";
        console.log(note.length);
      }

      noteBlocks = [
        {
          type: "section",
          text: {
            type: "mrkdwn",
            text: note
          },
          accessory: {
            type: "image",
            image_url: `https://cdn.glitch.com/0d5619da-dfb3-451b-9255-5560cd0da50b%2Fstickie_${color}.png`,
            alt_text: "stickie note"
          }
        },
        {
          type: "context",
          elements: [
            {
              type: "mrkdwn",
              text: o.timestamp
            }
          ]
        },
        {
          type: "divider"
        }
      ];
      blocks = blocks.concat(noteBlocks);
    }
  }

  // The final view -

  let view = {
    type: "home",
    title: {
      type: "plain_text",
      text: "Keep notes!"
    },
    // blocks: blocks
    blocks: blocks
  };

  return JSON.stringify(view);
};



/* Display App Home */

const displayHome = async (user, data) => {
  if (data) {
    // Store in a local DB
    db.push(`/${user}/data[]`, data, true);
  }

  if (user === 'U018DM5NAQ4') { // Kent
    const args = {
      token: process.env.SLACK_BOT_TOKEN,
      user_id: user,
      view: await updateView(user)
    };

    const result = await axios.post(
      `${apiUrl}/views.publish`,
      qs.stringify(args)
    );

    try {
      if (result.data.error) {
        console.log(result.data.error);
      }
    } catch (e) {
      console.log(e);
    }

  } else if (user === 'UE32RF9SB') { // Saeko
    const args = {
      token: process.env.SLACK_BOT_TOKEN,
      user_id: user,
      view: await updateView(user)
    };

    const result = await axios.post(
      `${apiUrl}/views.publish`,
      qs.stringify(args)
    );

    try {
      if (result.data.error) {
        console.log(result.data.error);
      }
    } catch (e) {
      console.log(e);
    }

  } else {
    const args = {
      token: process.env.SLACK_BOT_TOKEN,
      user_id: user,
      view: await updateViewOtherStaff(user)
    };
    const result = await axios.post(
      `${apiUrl}/views.publish`,
      qs.stringify(args)
    );

    try {
      if (result.data.error) {
        console.log(result.data.error);
      }
    } catch (e) {
      console.log(e);
    }
  }
};



/* Open a modal */

const openModal = async trigger_id => {
  const modal = {
    type: "modal",
    title: {
      type: "plain_text",
      text: "Create a stickie note"
    },
    submit: {
      type: "plain_text",
      text: "Create"
    },
    blocks: [
      // Text input
      {
        type: "input",
        block_id: "note01",
        label: {
          type: "plain_text",
          text: "Note"
        },
        element: {
          action_id: "content",
          type: "plain_text_input",
          placeholder: {
            type: "plain_text",
            text:
              "Take a note... \n(Text longer than 3000 characters will be truncated!)"
          },
          multiline: true
        }
      },

      // Drop-down menu
      {
        type: "input",
        block_id: "note02",
        label: {
          type: "plain_text",
          text: "Color"
        },
        element: {
          type: "static_select",
          action_id: "color",
          options: [
            {
              text: {
                type: "plain_text",
                text: "yellow"
              },
              value: "yellow"
            },
            {
              text: {
                type: "plain_text",
                text: "blue"
              },
              value: "blue"
            },
            {
              text: {
                type: "plain_text",
                text: "green"
              },
              value: "green"
            },
            {
              text: {
                type: "plain_text",
                text: "pink"
              },
              value: "pink"
            }
          ]
        }
      }
    ]
  };

  const args = {
    token: process.env.SLACK_BOT_TOKEN,
    trigger_id: trigger_id,
    view: JSON.stringify(modal)
  };

  const result = await axios.post(`${apiUrl}/views.open`, qs.stringify(args));

  //console.log(result.data);
};

module.exports = { displayHome, openModal };
