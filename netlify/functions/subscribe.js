exports.handler = async function(event) {
  if (event.httpMethod !== "POST") {
    return { statusCode: 405, body: "Method Not Allowed" };
  }

  const { email } = JSON.parse(event.body || "{}");

  if (!email) {
    return {
      statusCode: 400,
      body: JSON.stringify({ error: "Email required" })
    };
  }

  const res = await fetch(
    `https://api.beehiiv.com/v2/publications/${process.env.BEEHIIV_PUBLICATION_ID}/subscriptions`,
    {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${process.env.BEEHIIV_API_KEY}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        email,
        reactivate_existing: true,
        send_welcome_email: true,
        utm_source: "HeraldFeed Popup"
      })
    }
  );

  const data = await res.json();

  return {
    statusCode: res.status,
    body: JSON.stringify(data)
  };
};