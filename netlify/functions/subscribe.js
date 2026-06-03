exports.handler = async function(event) {
  if (event.httpMethod !== "POST") {
    return { statusCode: 405, body: "Method Not Allowed" };
  }

  try {
    const { email } = JSON.parse(event.body || "{}");

    const response = await fetch(
      `https://api.beehiiv.com/v2/publications/${process.env.BEEHIIV_PUBLICATION_ID}/subscriptions`,
      {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${process.env.BEEHIIV_API_KEY}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          email: email,
          reactivate_existing: true,
          send_welcome_email: true,
          utm_source: "HeraldFeed Popup"
        })
      }
    );

    const text = await response.text();

    console.log("Beehiiv status:", response.status);
    console.log("Beehiiv response:", text);

    return {
      statusCode: response.status,
      body: text
    };

  } catch (error) {
    console.error("Function error:", error.message);

    return {
      statusCode: 500,
      body: JSON.stringify({ error: error.message })
    };
  }
};