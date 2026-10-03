import http from 'node:http';

const escape = (value) => value.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('"', '&quot;');
const page = (body) => '<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Benchmark fixture</title></head><body><main>' + body + '</main></body></html>';

export async function startFixture() {
  const state = { logins: 0, projects: [], events: [] };
  const server = http.createServer(async (req, res) => {
    const url = new URL(req.url, 'http://localhost');
    const send = (status, body, headers = {}) => {
      res.writeHead(status, { 'content-type': 'text/html; charset=utf-8', ...headers });
      res.end(body);
    };
    const redirect = (location, headers = {}) => send(303, '', { location, ...headers });
    const authenticated = (req.headers.cookie ?? '').split('; ').includes('bench-session=signed-in');
    if (req.method === 'GET' && url.pathname === '/login') {
      return send(200, page('<h1>Sign in</h1><form method="post" action="/login"><label>Email <input name="email" type="email" required></label><label>Password <input name="password" type="password" required></label><button>Sign in</button></form>'));
    }
    if (req.method === 'POST') {
      let body = '';
      for await (const chunk of req) body += chunk;
      const values = new URLSearchParams(body);
      if (url.pathname === '/login') {
        if (values.get('email') !== 'bench@example.test' || values.get('password') !== 'demo-password') return send(401, page('<p role="alert">Incorrect credentials</p>'));
        state.logins++;
        state.events.push('login');
        return redirect('/projects', { 'set-cookie': 'bench-session=signed-in; HttpOnly; SameSite=Strict; Path=/' });
      }
      if (url.pathname === '/projects' && authenticated) {
        const name = values.get('name');
        const description = values.get('description');
        if (!name || !description) return send(400, page('<p role="alert">Name and description are required</p>'));
        const project = { id: state.projects.length + 1, name, description };
        state.projects.push(project);
        state.events.push('create-project');
        return redirect('/projects/' + project.id);
      }
    }
    if (!authenticated) return redirect('/login');
    if (url.pathname === '/projects') {
      return send(200, page('<h1>Projects</h1><p>No projects yet</p><a href="/projects/new">New project</a>'));
    }
    if (url.pathname === '/projects/new') {
      return send(200, page('<h1>New project</h1><form method="post" action="/projects"><label>Project name <input name="name" required></label><label>Description <textarea name="description" required></textarea></label><button>Create project</button></form>'));
    }
    const project = state.projects.find((p) => url.pathname === '/projects/' + p.id);
    if (project) return send(200, page('<p role="status">Project created</p><h1>' + escape(project.name) + '</h1><p>' + escape(project.description) + '</p><a href="/projects">Projects</a>'));
    send(404, page('<h1>Not found</h1>'));
  });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  return { server, url: 'http://127.0.0.1:' + server.address().port, state };
}

export function acceptance(state) {
  return state.logins === 1 && state.projects.length === 1 &&
    state.projects[0].name === 'Bench Project' &&
    state.projects[0].description === 'Token and speed benchmark' &&
    JSON.stringify(state.events) === JSON.stringify(['login', 'create-project']);
}
