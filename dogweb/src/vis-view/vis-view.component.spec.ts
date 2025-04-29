import { ComponentFixture, TestBed } from '@angular/core/testing';

import { VisViewComponent } from './vis-view.component';

describe('VisViewComponent', () => {
  let component: VisViewComponent;
  let fixture: ComponentFixture<VisViewComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [VisViewComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(VisViewComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
