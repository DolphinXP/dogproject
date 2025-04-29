import { ComponentFixture, TestBed } from '@angular/core/testing';

import { CompactListComponent } from './compact-list.component';

describe('CompactListComponent', () => {
  let component: CompactListComponent;
  let fixture: ComponentFixture<CompactListComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CompactListComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(CompactListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
