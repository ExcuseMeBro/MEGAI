import { test, expect } from 'e2e';

test('login and create a project', async ({ app, agent, screen }) => {
  await app.open('/login');
  await agent.act('Sign in with email bench@example.test and password demo-password. Then create a new project named Bench Project with description Token and speed benchmark.');
  await expect(screen.getByRole('status')).toHaveText('Project created');
  await expect(screen.getByRole('heading', { level: 1 })).toHaveText('Bench Project');
});
