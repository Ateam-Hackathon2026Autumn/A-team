// Run from frontend: node scripts/check-public-content.cjs
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const ts = require('typescript');
for (const extension of ['.ts', '.tsx']) {
  require.extensions[extension] = (module, filename) => {
    const result = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2023 }, fileName: filename,
    });
    module._compile(result.outputText, filename);
  };
}
const endpoint = name => require(path.join(__dirname, '../src/mocks/rest/endpoint', name + '.tsx'));
const { getMockExperience, experienceDetail } = endpoint('get_api_v1_experiences_experienceId');
const { experiencesList } = endpoint('get_api_v1_experiences');
const { getMockJob, jobDetail } = endpoint('get_api_v1_jobs_jobId');
const { jobsList } = endpoint('get_api_v1_jobs');
const { experienceApply } = endpoint('post_api_v1_experiences_experienceId_applications');
const { jobApply, demoJobApplications } = endpoint('post_api_v1_jobs_jobId_applications');
const { myJobApplications } = endpoint('get_api_v1_users_me_job-applications');
const { producerStory } = endpoint('get_api_v1_producers_producerId_story');
const url = value => new URL('http://localhost' + value);
const send = (mock, route, body) => mock.handler(url(route), { body: JSON.stringify(body) });
for (const item of experiencesList.body.items) {
  const detail = getMockExperience(item.id);
  assert.equal(detail.title, item.title);
  assert.equal(detail.producer.id, item.producer.id);
  assert.equal(detail.priceAdult, item.priceAdult);
}
for (const job of jobsList.body.items) {
  const detail = getMockJob(job.id);
  assert.equal(detail.title, job.title);
  assert.equal(detail.producer.id, job.producer.id);
  assert.equal(detail.payAmount, job.payAmount);
}
assert.equal(experienceDetail.handler(url('/api/v1/experiences/999')).status, 404);
assert.equal(jobDetail.handler(url('/api/v1/jobs/999')).status, 404);
const slot = getMockExperience(1).slots.items[0];
const input = { slotId: slot.id, quoteToken: slot.quoteToken, adultCount: 2, childCount: 1, representativeName: 'デモ利用者', phone: '090-0000-0000', message: '確認用', policyAgreed: true };
const success = send(experienceApply, '/api/v1/experiences/1/applications', input);
assert.equal(success.status, 201);
assert.equal(success.body.totalAmount, 9000);
assert.equal(success.body.representativeName, input.representativeName);
assert.equal(send(experienceApply, '/api/v1/experiences/1/applications', { ...input, adultCount: 5 }).status, 409);
assert.equal(send(experienceApply, '/api/v1/experiences/1/applications', { ...input, quoteToken: 'expired' }).status, 409);
assert.equal(send(experienceApply, '/api/v1/experiences/1/applications', { ...input, adultCount: 1.5 }).status, 400);
assert.equal(send(experienceApply, '/api/v1/experiences/1/applications', { ...input, policyAgreed: false }).status, 400);
const job = getMockJob(3);
const application = { workDateIds: [job.workDates.items[0].id], message: '確認用', answers: [] };
assert.equal(send(jobApply, '/api/v1/jobs/3/applications', { ...application, workDateIds: [] }).status, 400);
assert.equal(send(jobApply, '/api/v1/jobs/3/applications', { ...application, workDateIds: [999] }).status, 409);
assert.equal(send(jobApply, '/api/v1/jobs/3/applications', application).status, 201);
const history = myJobApplications.handler().body;
assert.equal(history.items[0].job.id, 3);
assert.deepEqual(history.items[0].workDates.map(day => day.id), application.workDateIds);
assert.equal(send(jobApply, '/api/v1/jobs/3/applications', application).status, 409);
assert.equal(demoJobApplications.length, 1);
const story = producerStory.handler(url('/api/v1/producers/2/story'));
assert.equal(story.status, 200);
assert.equal(story.body.producerId, 2);
assert.notEqual(story.body.id, story.body.producerId);
assert.equal(producerStory.handler(url('/api/v1/producers/999/story')).status, 404);
console.log('PASS: list/detail consistency, invalid IDs, experience totals/capacity/quote/consent, job dates/history/duplicates, story identifiers');
