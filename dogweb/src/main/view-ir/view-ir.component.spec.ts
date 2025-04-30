import {ComponentFixture, TestBed} from '@angular/core/testing';

import {ViewIrComponent} from './view-ir.component';

describe('ViewIrComponent', () => {
  let component: ViewIrComponent;
  let fixture: ComponentFixture<ViewIrComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ViewIrComponent]
    })
      .compileComponents();

    fixture = TestBed.createComponent(ViewIrComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
