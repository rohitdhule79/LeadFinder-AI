import pytest
from src.database.store import Store

def test_edit_resets_verified(tmp_path):
    store=Store(tmp_path/'db.sqlite')
    i=store.add_lead(dict(profile_url='https://linkedin.com/in/test-edit',source_url='https://example.org',full_name='Test',designation='Founder',country='India'))
    store.review(i,'Verified','Checked role/location against source')
    store.edit(i,{'company':'Updated company'})
    row=store.list_leads()[0]
    assert row['company']=='Updated company' and row['verification_status']=='Unverified'
    with pytest.raises(ValueError): store.edit(i,{'profile_url':'https://evil.org'})
