import {ComponentFixture, TestBed} from '@angular/core/testing';

import {ViewVisComponent} from './view-vis.component';

describe('VisViewComponent', () => {
  let component: ViewVisComponent;
  let fixture: ComponentFixture<ViewVisComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ViewVisComponent]
    })
      .compileComponents();

    fixture = TestBed.createComponent(ViewVisComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
