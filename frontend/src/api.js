// Every call carries the logged-in person's token: a plain fetch goes out
// anonymous and gets 401, because Volto adds the token only through its
// own API helper.
export const apiUrl = (path) => `/++api++/${path.replace(/^\//, '')}`;

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

const headers = (token) => ({
  Accept: 'application/json',
  ...(token ? { Authorization: `Bearer ${token}` } : {}),
});

export const getJson = async (token, path) => {
  const response = await fetch(apiUrl(path), {
    headers: headers(token),
    credentials: 'same-origin',
  });
  let data = null;
  try {
    data = await response.json();
  } catch (e) {
    data = null;
  }
  if (!response.ok) {
    throw new ApiError(
      data?.error?.message || 'Something went wrong. Please try again.',
      response.status,
    );
  }
  return data;
};

// A download needs the token too, so it can't be a plain link: fetch it
// and hand the browser a blob.
export const download = async (token, path, filename) => {
  const response = await fetch(apiUrl(path), {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    credentials: 'same-origin',
  });
  if (!response.ok) throw new ApiError('The download failed.', response.status);
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
};
